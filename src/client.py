from typing import Coroutine, Iterable, Optional, Tuple, Union, Dict, List, Any
from asyncio import get_event_loop
from asyncio.coroutines import iscoroutinefunction
from websockets import connect

from utils import is_int, prefix_to_dict
from message import Message
from errors import *
from user_events import *
from abcs import State
from channel import Channel
from member import Member


# class Client, it will create bots
class Client: 
    def __init__(self, token: str, login: str) -> None:
        self.token = token
        self.login = login
        self._channels: Dict[int, Channel] = {}  # dict of Channel-objects
        self._channels_names: Dict[str, int] = {}  # dict of name_channel : id_channel
        self._ws: Optional[connect] = None
        self.loop = get_event_loop()
        self.global_state: Optional[Client.GlobalState] = None
        self._local_states: Dict[str, Dict[str, str]] = {}
        self._delayed_msgs: Dict[str, List[str]] = {}
        self._disconnected_id: List[int] = []

    def run(self, channels: Iterable[str], *, ws_params: Dict[str, Any] = None) -> None:
        """
        this function starts event listener, use it if you want to start 'Client' as single worker.\n
        If you want start 'Client' with any other async code - look 'start()'

        Args:
            channels: Iterable[str]
                Iterable object with names of channel to join
            ws_params: Dict[str, Any]
                Dict with arguments for websockets.connect
        """
        self.loop.create_task(self.start(channels, ws_params=ws_params))
        self.loop.run_forever()

    async def start(self, channels: Iterable[str], *, ws_params: Dict = None) -> None:
        """
        |coro|
        this function starts event listener. \n
        If you won't combine this with any other async code - you can use 'run()'.

        Args:
            channels: Iterable[`str`]
                Iterable object with names of channel to join
            ws_params: Dict[str, Any]
                Dict with arguments for websockets.connect
        """
        # creating websocket
        uri = 'wss://irc-ws.chat.twitch.tv:443'
        if not ws_params: ws_params = {}
        self._ws = await connect(uri, **ws_params)
        # asking server to capability
        await self._send('CAP REQ :twitch.tv/membership')
        await self._send('CAP REQ :twitch.tv/commands')
        await self._send('CAP REQ :twitch.tv/tags')
        # loging
        await self._send(f'PASS {self.token}')
        await self._send(f'NICK {self.login}')
        # joining the channels
        for channel in channels:
            self._to_do(self._send(f'JOIN #{channel.lower()}'))

        # loop to receive, split and handle messages we got
        while True:
            received_msgs = await self._ws.recv()
            for received_msg in received_msgs.split('\r\n'):
                # sometimes we'll receive more then 1 msg from server and
                # if so - i like to create tasks and don't call them
                # before we finish current loop
                self._to_do(self._handle_message(received_msg))

    async def _handle_message(self, msg: str) -> None:
        # if we got empty msg - skip
        if len(msg) == 0:
            return
        # sometimes (about once in 5 minutes) we'll receive PING
        # that means server is checking we still alive
        # we must send PONG to server for make it doesn't close the connection
        if msg.startswith('PING'):
            self._to_do(self._send('PONG :tmi.twitch.tv'))
            return
        # parse the message that we got into tags, command and text
        tags, command, text = await self._parse_message(msg)
        # some system info will have integer as command-type
        if is_int(command[1]):  # if command is some integer
            if command[1] == '353':  # if 353 - it's namelist of channel
                channel_name = command[4][1:].lower()  # channel name
                id = self._channels_names.get(channel_name)  # id of current channel
                if id is not None:  # if we got id - channel is exist, so just append names_list of this channel
                    self._channels[id].nameslist.extend(text.split(' '))
                else:  # esle - channel isn't exist - putting msg to delayed handle
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
            elif command[1] not in ['001', '002', '003', '004', '375', '372', '376', '366']:
                raise UnknownIntCommand(msg)
            return

        # messages from users in a channel will contains 'PRIVMSG'
        elif command[1] == 'PRIVMSG':
            if hasattr(self, 'on_message'):  # if event registered
                channel_id = int(tags['room-id'])  # getting channel id
                channel = self._channels[channel_id]  # getting channel by id
                author = Member(channel, tags)  # creating Member
                message = Message(channel, author, text, tags)  # creating Message
                self._to_do(self.on_message(message))  # call event
            return

        # When someone JOIN a channel
        elif command[1] == 'JOIN':
            if hasattr(self, 'on_join'):
                user_name = command[0].split('!', 1)[0]
                channel_name = command[2][1:]
                id = self._channels_names.get(channel_name)
                if id is not None:
                    self._to_do(self.on_join(self._channels[id], user_name))
            return

        # When some one LEFT a channel
        elif command[1] == 'PART':
            if hasattr(self, 'on_left'):
                user_name = command[0].split('!', 1)[0]
                channel_name = command[2][1:]
                id = self._channels_names[channel_name]
                self._to_do(self.on_left(self._channels[id], user_name))
            return

        # on NOTICE
        elif command[1] == 'NOTICE':
            if tags['msg-id'] == 'msg_room_not_found':
                print(f'Channel {command[2]} is not found!')
            elif hasattr(self, 'on_notice'):
                notice_id = tags['msg-id']
                channel_name = command[2][1:]
                id = self._channels_names.get(channel_name)
                if id is None:  # if we recive this before ROOMSTATE put this message to delayed handle
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                    return  # and return cuz we haven't channel

                self._to_do(self.on_notice(self._channels[id],
                                           notice_id,
                                           text))
            return

        # user_events - Sub, sub-gift, ritual, raid...
        elif command[1] == 'USERNOTICE':
            if hasattr(self, 'on_user_event'):
                channel = self._channels.get(int(tags['room-id']))
                if channel is None:  # if we recieve this before ROOMSTATE put this message to delayed handle
                    channel_name = command[2][1:]  # getting name of channel
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                    return  # and return cuz we haven't channel

                author = Member(channel, tags)
                event_type = tags['msg-id']
                # choosing event type
                if event_type == 'sub' or event_type == 'resub':
                    event = Sub(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'subgift' or event_type == 'anonsubgift':
                    event = SubGift(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'giftpaidupgrade' or event_type == 'anongiftpaidupgrade':
                    event = GiftPaidUpgrade(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'ritual':
                    event = Ritual(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'bitsbadgetier':
                    event = BitsBadgeTier(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'raid':
                    print('raid'.upper(), '\nmsg is', msg, 'tags =', tags)
                    event = Raid(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'unraid':
                    print('unraid'.upper(), '\nmsg is', msg, 'tags =', tags)
                    event = UnRaid(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'submysterygift':
                    event = SubMysteryGift(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'rewardgift':
                    event = RewardGift(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'communitypayforward':
                    event = CommunityPayForward(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'primepaidupgrade':
                    event = PrimePaidUpgrade(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))

                elif event_type == 'standardpayforward':
                    event = StandardPayForward(author, channel, tags, text)
                    self._to_do(self.on_user_event(event))
                else:
                    raise UnknownUserNotice(event_type, msg)

        elif command[1] == 'CLEARCHAT':
            if text is not None and hasattr(self, 'on_clear_user'):
                channel_name = command[2][1:]
                id = self._channels_names[channel_name]
                user_name = text
                ban_duration = tags.get('ban-duration')
                if ban_duration is not None:
                    ban_duration = int(ban_duration)
                self._to_do(self.on_clear_user(self._channels[id],
                                               user_name,
                                               ban_duration))

            elif text is None and hasattr(self, 'on_clear_chat'):
                channel_name = command[2][1:]
                id = self._channels_names[channel_name]
                self._to_do(self.on_clear_chat(self._channels[id]))
            return

        elif command[1] == 'CLEARMSG':
            if hasattr(self, 'on_clear_message'):
                channel_name = command[2][1:]
                id = self._channels_names[channel_name]
                user_name = tags['login']
                message_id = tags['target-msg-id']
                self._to_do(self.on_clear_message(self._channels[id],
                                                  user_name,
                                                  text,
                                                  message_id))

        elif command[1] == 'HOSTTARGET':
            viewers = text.split(' ')
            # we may get (<channel> [<number-of-viewers>]) if channel start host
            if viewers[0] != '-' and hasattr(self, 'on_start_host'):
                channel_name = command[2][1:]

                id = self._channels_names.get(channel_name)
                if id is None:  # if we recive this before ROOMSTATE put this message to delayed handle
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                    return

                hoster = viewers[0]  # name of hoster
                viewers = 0 if (viewers[1] == '-') else int(viewers[1])  # count of viewers

                self._to_do(self.on_start_host(self._channels[id],
                                               viewers,
                                               hoster))

            # we may get (- [<number-of-viewers>]) if channel stop host
            elif viewers[0] == '-' and hasattr(self, 'on_stop_host'):
                channel_name = command[2][1:]
                id = self._channels_names[channel_name]
                viewers = int(viewers[1])
                self._to_do(self.on_stop_host(self._channels[id],
                                              viewers))
            else:
                raise UnknownHostTarget(msg)
            return

        elif command[1] == 'RECONNECT':
            for channel in self._channels_names:
                self._to_do(self._send(f'JOIN #{channel.lower()}'))
                print("!\n\nWE GOT RECONNECT command!\n\n!")

        # or we get info about channel we joined,
        # or about updates in that channel
        elif command[1] == 'ROOMSTATE':
            id = int(tags['room-id'])  # id of channel

            if len(tags) == 7:  # if we get 7 tags, it's info
                channel_name = command[2][1:]  # channel_name of channel
                mystate_tags = self._local_states.pop(channel_name)  # getting mystate and delete it
                # create channel
                self._channels[id] = Channel(channel_name, mystate_tags, self._ws, tags)
                self._channels_names[channel_name] = id  # save pair of name_chnl : id_chnl

                delayed_msgs = self._delayed_msgs.pop(channel_name, [])  # get list of delayed msgs
                while delayed_msgs:  # while list is not empety
                    msg = delayed_msgs.pop()  # delete one msg from list
                    self._to_do(self._handle_message(msg))  # and put it to handle

                if hasattr(self, 'on_room_join'):  # if event is registered
                    self._to_do(self.on_room_join(self._channels[id]))  # call event

            elif len(tags) == 2:  # if we get 2 tags, it's update of room
                tags.pop('room-id')  # dellete channel id to tags contains only one tag
                key, value = tags.popitem()  # getting 'key' and new 'value'

                if hasattr(self, 'on_room_update'):  # if event is registered
                    before = self._channels[id].get(key)  # getting before
                    self._channels[id].update(key, value)  # update
                    after = self._channels[id].get(key)  # getting after
                    self._to_do(self.on_room_update(self._channels[id],
                                                    key,
                                                    before,
                                                    after))

                else:  # if event isn't registered - just update
                    self._channels[id].update(key, value)
            else:
                raise UnknownRoomState(msg)  # we can't get anything else
            return

        # we receive USERSTATE after we joined a channel, it contains our local state for the channel
        elif command[1] == 'USERSTATE':
            channel_name = command[2][1:]
            self._local_states[channel_name] = tags
            return

        # 'GLOBALUSERSTATE' means it's message with info about us( about our bot )
        elif command[1] == 'GLOBALUSERSTATE':
            self.global_state = Client.GlobalState(tags)
            if hasattr(self, 'on_login'):  # if even registered - call it
                self._to_do(self.on_login())
            return
        elif command[1] == 'CAP':
            return
        else:
            raise UnknownCommand(msg)

    @staticmethod
    async def _parse_message(msg: str) -> Tuple[Dict[str, str], List[str], Optional[str]]:
        text = None
        
        # we may don't receive tags, if so we won't have space before colon
        if msg.startswith(':'):
            parts = msg.split(':', 2)
        # if we receive tags, they startswith '@', so we have to split by ' :'
        # because tags may contain ':' but can't contain ' :' (space+colon)
        elif msg.startswith('@'):
            parts = msg.split(' :', 2)
        else:
            raise WrongMessageStruct(msg)
        # create dict = <tag_name>: <value>
        # if we received tags, we deleting '@' in parts[0][1:]
        tags = prefix_to_dict(parts[0][1:])
        command = parts[1].split(' ')
        # we may don't receive text, if so - text is None
        if len(parts) == 3:
            text = parts[2]
        return tags, command, text

    async def _send(self, command: str) -> str:
        await self._ws.send(command + '\r\n')
        return command

    async def send_msg(self, channel: Union[int, str, Channel], text: str):
        if type(channel) == Channel:
            channel = channel.name
        elif type(channel) == int:
            channel = self._channels[channel].name
        command = f'PRIVMSG #{channel} :{text}'
        self._to_do(self._send(command))

    async def join(self, channel: str):
        self._to_do(self._send(f'JOIN #{channel.lower()}'))

    def event(self, coro: Coroutine) -> Coroutine:
        """
        register event

        Args:
            coro: Coroutine
                an Coroutine that will be called when the event would be happened

        Raises:
            errors.UnknownEvent
                if got unknown name of event
            errors.FunctionIsNotCorutine
                if object is not Coroutine

        Returns:
            Coroutine
                object we got in coro argument, use for multiple decorate
        """
        events = ('on_message', 'on_room_update', 'on_login', 'on_room_join',
                  'on_join', 'on_left', 'on_clear_user', 'on_clear_chat',
                  'on_clear_message', 'on_start_host', 'on_stop_host',
                  'on_notice', 'on_user_event')
        if not iscoroutinefunction(coro):  # func must be coroutine ( use async def ...(): pass )
            raise FunctionIsNotCorutine(coro.__name__)
        if coro.__name__ in events:  # if we know event we got
            setattr(self, coro.__name__, coro)
            return coro  # return coro
        else:
            # what for a developer will register unknown event?
            # better tell him/her about
            raise UnknownEvent(coro.__name__)
    
    def _to_do(self, coro: Coroutine):
        self.loop.create_task(coro)

    class GlobalState(State):
        def __init__(self, tags):
            super().__init__(tags)
            self.color = tags['color']
            self.name = tags['display-name']
            self.emotes = tuple(map(int, tags['emote-sets'].split(',')))
            self.id = int(tags['user-id'])

