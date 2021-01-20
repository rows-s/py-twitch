from copy import copy
from typing import Coroutine, Iterable, Optional, Tuple, Union, Dict, List, Any, Awaitable
from asyncio import get_event_loop
from asyncio.coroutines import iscoroutinefunction
from websockets import connect, WebSocketClientProtocol

from utils import is_int, prefix_to_dict
from irc_message import Message
from errors import *
from irc_user_events import *
from abcs import StateABC
from irc_channel import Channel
from irc_member import Member


__all__ = ['Client']


# class Client, it will create bots
class Client:
    _user_events_types: Dict[str, Tuple[str, Any]] = {
        'sub': ('on_sub', Sub),
        'resub': ('on_sub', Sub),
        'subgift': ('on_sub_gift', SubGift),
        'anonsubgift': ('on_sub_gift', SubGift),
        'rewardgift': ('on_reward_gift', RewardGift),
        'submysterygift': ('on_sub_mistery_gift', SubMysteryGift),
        'primepaidupgrade': ('on_prime_paid_upgrate', PrimePaidUpgrade),
        'giftpaidupgrate': ('on_gift_paid_upgrade', GiftPaidUpgrade),
        'anongiftpaidupgrate': ('on_gift_paid_upgrade', GiftPaidUpgrade),
        'standardpayforward': ('on_standard_pay_forward', StandardPayForward),
        'communitypayforward': ('on_community_pay_forward', CommunityPayForward),
        'bitsbadgetier': ('on_bits_badge_tier', BitsBadgeTier),
        'raid': ('on_raid', Raid),
        'unraid': ('on_unraid', UnRaid),
        'ritual': ('on_ritual', Ritual)
    }

    _events_names = (
        'on_message',  # PRIVMSG
        'on_room_update', 'on_room_join',  # ROOMSTATE
        'on_login',  # GLOBALUSERSTATE
        'on_join',  # JOIN
        'on_left',  # PART
        'on_clear_user', 'on_clear_chat',  # CLEARCHAT
        'on_message_delete',  # CLEARMSG
        'on_start_host', 'on_stop_host',  # HOSTTARGET
        'on_notice',  # NOTICE
        'on_user_event'  # USERNOTICE
    )

    _user_events_names = (
        'on_sub', 'on_sub_gift', 'on_reward_gift', 'on_sub_mistery_gift',  # subs
        'on_prime_paid_upgrate', 'on_gift_paid_upgrade',  # upgrades
        'on_standard_pay_forward', 'on_community_pay_forward',  # payments forward
        'on_bits_badge_tier',  # bits badges tier
        'on_raid', 'on_unraid',  # raids
        'on_ritual'  # rituals
    )

    def __init__(
            self,
            token: str,
            login: str
    ) -> None:
        self.token = token
        self.login = login
        self.loop = get_event_loop()
        self.global_state: Optional[Client.GlobalState] = None
        self._channels: Dict[int, Channel] = {}  # dict of id_channel: Channel
        self._channels_names: Dict[str, int] = {}  # dict of name_channel : id_channel
        self._ws: Optional[WebSocketClientProtocol] = None
        self._local_states: Dict[str, Dict[str, str]] = {}
        self._delayed_msgs: Dict[str, List[str]] = {}

    def run(
        self, 
        channels: Iterable[str], 
        *, 
        ws_params: Dict[str, Any] = None
    ) -> None:
        """
        the method starts event listener, use it if you want to start 'Client' as single worker.\n
        If you want start 'Client' with any other async code - look 'start()'

        Args:
            channels: Iterable[str]
                Iterable object with names of channel to join
            ws_params: Dict[str, Any]
                Dict with arguments for websockets.connect
        """
        self.loop.run_until_complete(self.start(channels, ws_params=ws_params))

    async def start(
            self,
            channels: Iterable[str],
            *,
            ws_params: Dict = None
    ) -> None:
        """
        |Coroutine|
        starts event listener. \n
        If you won't combine this with any other async code - you can use 'run()'.

        Args:
            channels: Iterable[`str`]
                Iterable object with names of channel to join
            ws_params: Dict[str, Any]
                Dict with arguments for websockets.connect
        """

        uri = 'wss://irc-ws.chat.twitch.tv:443'
        if ws_params is None:
            ws_params = {}
        self._ws = await connect(uri, **ws_params)
        # capability
        await self._send('CAP REQ :twitch.tv/membership')
        await self._send('CAP REQ :twitch.tv/commands')
        await self._send('CAP REQ :twitch.tv/tags')
        # loging
        await self._send(f'PASS {self.token}')
        await self._send(f'NICK {self.login}')
        # joining channels
        for channel in channels:
            self._do_later(self._send(f'JOIN #{channel.lower()}'))
        # handling loop
        while True:
            received_msgs = await self._ws.recv()
            for received_msg in received_msgs.split('\r\n'):
                self._do_later(self._handle_message(received_msg))

    async def _handle_message(self, msg: str) -> None:
        # if empty message
        if len(msg) == 0:
            return
        # if connection checking
        if msg.startswith('PING'):
            self._do_later(self._send('PONG :tmi.twitch.tv'))
            return
        # selecting parts
        tags, command, text = await self._parse_message(msg)
        # if system message
        if is_int(command[1]):
            # part of namelist of a channel
            if command[1] == '353':  
                channel_name = command[4][1:].lower() 
                try:
                    channel_id = self._channels_names[channel_name]
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                else:
                    names: list = text.split(' ')
                    channel = self._channels[channel_id]
                    channel.nameslist.extend(names)
            # others
            elif command[1] not in ['001', '002', '003', '004', '375', '372', '376', '366']:
                raise UnknownIntCommand(msg)
        # if message in a channel
        elif command[1] == 'PRIVMSG':
            if hasattr(self, 'on_message'):
                channel_id = int(tags['room-id'])
                channel = self._channels[channel_id]
                author = Member(channel, tags) 
                message = Message(channel, author, text, tags)
                self._do_later(
                    self.on_message(message)
                )
        # if a joining
        elif command[1] == 'JOIN':
            if hasattr(self, 'on_join'):
                channel_name = command[2][1:]
                try:
                    channel_id = self._channels_names[channel_name]
                    channel = self._channels[channel_id]
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                else:
                    user_name = command[0].split('!', 1)[0]
                    self._do_later(
                        self.on_join(channel, user_name)
                    )
        # if a leaving
        elif command[1] == 'PART':
            if hasattr(self, 'on_left'):
                user_name = command[0].split('!', 1)[0]
                channel_name = command[2][1:]
                channel_id = self._channels_names[channel_name]
                channel = self._channels[channel_id]
                self._do_later(
                    self.on_left(channel, user_name)
                )
        # if a NOTICE
        elif command[1] == 'NOTICE':
            notice_id = tags['msg-id']
            if notice_id == 'msg_room_not_found':
                print(f'Channel {command[2]} is not found!')
            elif hasattr(self, 'on_notice'):
                channel_name = command[2][1:]
                try:
                    channel_id = self._channels_names[channel_name]
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                else:
                    channel = self._channels[channel_id]
                    self._do_later(
                        self.on_notice(channel, notice_id, text)
                    )
        # if a user event
        elif command[1] == 'USERNOTICE':
            if hasattr(self, 'on_user_event'):
                channel_id = int(tags['room-id'])
                try:
                    channel = self._channels[channel_id]
                # if doesn't exist
                except KeyError:
                    channel_name = command[2][1:]
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                    return
                # main variables
                author = Member(channel, tags)
                event_type = tags['msg-id']
                # choosing event type
                try:
                    event_attr, event_class = Client._user_events_types[event_type]
                # if unknown event
                except KeyError:
                    if hasattr(self, 'on_unknown_user_event'):
                        pass
                # if known event
                else:
                    # if has specified event handler
                    if hasattr(self, event_attr):
                        event_handler = getattr(self, event_attr)
                        event = event_class(author, channel, tags, text)
                        self._do_later(event_handler(event))
                    # else -> if has global handler
                    elif hasattr(self, 'on_user_event'):
                        event = event_class(author, channel, tags, text)
                        self._do_later(
                            self.on_user_event(event)
                        )
        # if `clear chat` or `clear user`
        elif command[1] == 'CLEARCHAT':
            # ob clear user
            if text is not None and hasattr(self, 'on_clear_user'):
                channel_name = command[2][1:]
                channel_id = self._channels_names[channel_name]
                user_name = text
                ban_duration = tags.get('ban-duration')
                if ban_duration is not None:
                    ban_duration = int(ban_duration)
                self._do_later(
                    self.on_clear_user(self._channels[channel_id], user_name, ban_duration)
                )
            # on clear chat
            elif text is None and hasattr(self, 'on_clear_chat'):
                channel_name = command[2][1:]
                channel_id = self._channels_names[channel_name]
                self._do_later(
                    self.on_clear_chat(self._channels[channel_id])
                )
            return
        # if message delete
        elif command[1] == 'CLEARMSG':
            if hasattr(self, 'on_message_delete'):
                channel_name = command[2][1:]
                channel_id = self._channels_names[channel_name]
                channel = self._channels[channel_id]
                user_name = tags['login']
                message_id = tags['target-msg-id']
                self._do_later(
                    self.on_message_delete(channel, user_name, text, message_id)
                )
        # if host start or stop
        elif command[1] == 'HOSTTARGET':
            if hasattr(self, 'on_start_host') or \
               hasattr(self, 'on_stop_host'):
                channel_name = command[2][1:]
                try:
                    channel_id = self._channels_names[channel_name]
                    channel = self._channels[channel_id]
                # if doesn't exist
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(msg)
                    return
                hoster, viewers_count = text.split(' ')
                # start
                if hoster != '-' and hasattr(self, 'on_start_host'):
                    self._do_later(
                        self.on_start_host(channel, int(viewers_count), hoster)
                    )
                # stop
                elif hoster == '-' and hasattr(self, 'on_stop_host'):
                    self._do_later(
                        self.on_stop_host(channel, int(viewers_count[1]))
                    )
                else:
                    raise UnknownHostTarget(msg)
        # if reconnecting request
        elif command[1] == 'RECONNECT':
            for channel in self._channels_names:
                self._do_later(self._send(f'JOIN #{channel.lower()}'))
        # if room joined or room updated
        elif command[1] == 'ROOMSTATE':
            channel_id = int(tags['room-id'])
            room_info_length = 7  # room join
            room_update_length = 2  # room_update
            # if room join
            if len(tags) == room_info_length:
                channel_name = command[2][1:]
                mystate_tags = self._local_states.pop(channel_name)
                # create channel
                self._channels[channel_id] = Channel(channel_name, mystate_tags, self._ws, tags)
                self._channels_names[channel_name] = channel_id
                # do later delayed messages
                delayed_msgs = self._delayed_msgs.pop(channel_name, [])
                while delayed_msgs:
                    msg = delayed_msgs.pop(0)
                    self._do_later(self._handle_message(msg))
                # event handle
                if hasattr(self, 'on_room_join'):
                    self._do_later(
                        self.on_room_join(self._channels[channel_id])
                    )
            # if room update
            elif len(tags) == room_update_length:
                tags.pop('room-id')  # need to only one key for the next row
                key, value = tags.popitem()
                # event handle
                if hasattr(self, 'on_room_update'):
                    channel = self._channels[channel_id]
                    # before
                    before = copy(channel)
                    before.nameslist = copy(channel.nameslist)
                    # update
                    channel.update(key, value)
                    # after
                    after = copy(channel)
                    after.nameslist = copy(channel.nameslist)
                    self._do_later(
                        self.on_room_update(self._channels[channel_id], before,  after)
                    )
                # if hasn't handler
                else:
                    channel = self._channels[channel_id]
                    channel.update(key, value)
            # if anything else
            else:
                raise UnknownRoomState(msg)  # we must not recive others ROOMSTATEs
        # if our local state
        elif command[1] == 'USERSTATE':
            channel_name = command[2][1:]
            self._local_states[channel_name] = tags
        # if our global state
        elif command[1] == 'GLOBALUSERSTATE':
            self.global_state = Client.GlobalState(tags)
            if hasattr(self, 'on_login'):  # if even registered - call it
                self._do_later(self.on_login())
        elif command[1] == 'CAP':
            return
        else:
            raise UnknownCommand(msg)

    @staticmethod
    async def _parse_message(message: str) -> Tuple[Dict[str, str], List[str], Optional[str]]:
        # if hasn't tags
        if message.startswith(':'):
            raw_parts = message.split(':', 2)
        # if has tags
        elif message.startswith('@'):
            raw_parts = message.split(' :', 2)
        else:
            raise InvalidMessageStruct(message)
        # raws
        if len(raw_parts) == 3:
            raw_tags, raw_command, text = raw_parts
        elif len(raw_parts) == 2:
            raw_tags, raw_command = raw_parts
            text = None
        else:
            raise InvalidMessageStruct(message)
        # tags
        tags = prefix_to_dict(raw_tags[1:])  # remove @ in the start
        # command
        command = raw_command.split(' ')
        return tags, command, text

    async def _send(self, command: str):
        await self._ws.send(command + '\r\n')

    async def send_msg(self, channel: Union[int, str, Channel], text: str):
        if type(channel) == Channel:
            channel = channel.name
        elif type(channel) == int:
            channel = self._channels[channel].name
        command = f'PRIVMSG #{channel} :{text}'
        await self._send(command)

    async def join(self, channel: str):
        self._do_later(self._send(f'JOIN #{channel.lower()}'))

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
            Coroutine:
                the object we got in coro argument (for multiple decorate)
        """

        if not iscoroutinefunction(coro):  # func must be coroutine ( use async def ...(): pass )
            raise FunctionIsNotCorutine(coro.__name__)
        # if event
        if coro.__name__ in Client._events_names:
            setattr(self, coro.__name__, coro)
            return coro
        # if user event
        elif coro.__name__ in Client._user_events_names:
            setattr(self, coro.__name__, coro)
            return coro
        # if unknown
        else:
            # what for a developer will register unknown event? better tell him/her about
            raise UnknownEvent(coro.__name__)
    
    def _do_later(self, coro: Awaitable):
        self.loop.create_task(coro)

    class GlobalState(StateABC):
        def __init__(self, tags):
            super().__init__(tags)
            self.color = tags['color']
            self.name = tags['display-name']
            self.emotes = tuple(map(int, tags['emote-sets'].split(',')))
            self.id = int(tags['user-id'])
