from copy import copy
from typing import Coroutine, Iterable, Tuple, Union, Any, Awaitable
from asyncio import get_event_loop
from asyncio.coroutines import iscoroutinefunction
from websockets import connect, WebSocketClientProtocol

from abcs import StateABC
from errors import *
from irc_user_events import *
from irc_message import Message
from irc_member import Member
from irc_channel import Channel
from utils import is_int, parse_raw_tags


__all__ = ['Client']


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

    events_names = (
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

    user_events_names = (
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
        # login details
        self.token = token
        self.login = login
        # Channels
        self._channels_by_id: Dict[str, Channel] = {}  # dict of id_channel: Channel
        self._channels_by_name: Dict[str, Channel] = {}  # dict of name_channel : id_channel
        # non-protected
        self.loop = get_event_loop()
        self.global_state: Optional[Client.GlobalState] = None
        # protected
        self._ws: Optional[WebSocketClientProtocol] = None
        self._local_states_tags: Dict[str, Dict[str, str]] = {}
        self._delayed_msgs: Dict[str, List[str]] = {}
        self._channels_nameslists: Dict[str, List[str]] = {}
        self._count_channels_to_prepare: int = 0

    #################################
    # method to get and properties
    #
    def get_channel_by_id(self, channel_id: str, default: Any = None):
        return self._channels_by_id.get(channel_id, default)

    def get_channel_by_name(self, channel_name: str, default: Any = None):
        return self._channels_by_name.get(channel_name, default)
    #
    # end of method to "getters" and properties
    #################################

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
            ws_params: Dict[`str`, Any]
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
        channels = copy(channels)  # we'll modify this
        for channel in channels:
            self._do_later(self._send(f'JOIN #{channel.lower()}'))
        self._count_channels_to_prepare = len(channels)
        # prepare
        # await self._prepare()
        # handling loop
        while True:
            irc_messages = await self._ws.recv()
            for irc_message in irc_messages.split('\r\n'):
                self._do_later(self._handle_message(irc_message))

    async def _prepare(self):
        while True in [True]:
            irc_messages = await self._ws.recv()
            for irc_message in irc_messages.split('\r\n'):
                # if empty
                if len(irc_message) == 0:
                    return
                # base variables
                tags, command, text = await self._parse_message(irc_message)
                command_type = command[1]
                # if part of nameslist
                if command_type == '353':
                    self._handle_nameslist_part(tags, command, text)
                # if end of nameslist
                elif command_type == '366':
                    try:
                        await self._handle_nameslist_end(tags, command, text)
                    except TooEarlyMessage:
                        channel_name = command[4][1:].lower()
                        self._delayed_msgs.setdefault(channel_name)
                elif command_type == 'NOTICE':
                    try:
                        self._handle_notice(tags, command, text)
                    except InvalidChannelName as e:
                        self._count_channels_to_prepare -= 1
                        print(e.args[0])  # description string
                elif command_type == 'ROOMSTATE':
                    pass

    async def _handle_message(self, irc_message: str) -> None:
        # if empty message
        if len(irc_message) == 0:
            return
        # if connection checking
        if irc_message.startswith('PING'):
            self._do_later(self._send('PONG :tmi.twitch.tv'))
            return
        # selecting parts
        tags, command, text = await self._parse_message(irc_message)
        command_type = command[1]
        # if system message
        if is_int(command_type):
            # part of namelist of a channel
            if command_type == '353':
                self._handle_nameslist_part(tags, command, text)
            # if end of nameslist
            elif command_type == '366':
                try:
                    self._handle_nameslist_end(tags, command, text)
                except TooEarlyMessage:
                    channel_name = command[4][1:].lower()
                    channel_delayed_msgs = self._delayed_msgs.setdefault(channel_name, [])
                    channel_delayed_msgs.append(irc_message)
        # if message in a channel
        elif command_type == 'PRIVMSG':
            if hasattr(self, 'on_message'):
                channel_id = tags['room-id']
                channel = self._channels_by_id[channel_id]
                author = Member(channel, tags) 
                message = Message(channel, author, text, tags)
                self._do_later(
                    self.on_message(message)
                )
        # if joining
        elif command_type == 'JOIN':
            if hasattr(self, 'on_join'):
                channel_name = command[2][1:]
                try:
                    channel = self._channels_by_name[channel_name]
                # if doesn't exist
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(irc_message)
                # if exist
                else:
                    user_name = command[0].split('!', 1)[0]
                    self._do_later(
                        self.on_join(channel, user_name)
                    )
        # if leaving
        elif command_type == 'PART':
            if hasattr(self, 'on_left'):
                user_name = command[0].split('!', 1)[0]
                channel_name = command[2][1:]
                channel = self._channels_by_name[channel_name]
                self._do_later(
                    self.on_left(channel, user_name)
                )
        # if NOTICE
        elif command_type == 'NOTICE':
            self._handle_notice(tags, command, text)
            if hasattr(self, 'on_notice'):
                notice_id = tags['msg-id']
                channel_name = command[2][1:]
                try:
                    channel = self._channels_by_name[channel_name]
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(irc_message)
                else:
                    self._do_later(
                        self.on_notice(channel, notice_id, text)
                    )
        # if user event
        elif command_type == 'USERNOTICE':
            if hasattr(self, 'on_user_event'):
                channel_id = tags['room-id']
                try:
                    channel = self._channels_by_id[channel_id]
                # if doesn't exist
                except KeyError:
                    channel_name = command[2][1:]
                    self._delayed_msgs.setdefault(channel_name, []).append(irc_message)
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
        elif command_type == 'CLEARCHAT':
            # if clear user
            if text is not None and hasattr(self, 'on_clear_user'):
                channel_name = command[2][1:]
                channel = self._channels_by_name[channel_name]
                user_name = text
                ban_duration = tags.get('ban-duration')
                if ban_duration is not None:
                    ban_duration = int(ban_duration)
                self._do_later(
                    self.on_clear_user(channel, user_name, ban_duration)
                )
            # if clear chat
            elif text is None and hasattr(self, 'on_clear_chat'):
                channel_name = command[2][1:]
                channel = self._channels_by_name[channel_name]
                self._do_later(
                    self.on_clear_chat(channel)
                )
            return
        # if message delete
        elif command_type == 'CLEARMSG':
            if hasattr(self, 'on_message_delete'):
                channel_name = command[2][1:]
                channel = self._channels_by_name[channel_name]
                user_name = tags['login']
                message_id = tags['target-msg-id']
                self._do_later(
                    self.on_message_delete(channel, user_name, text, message_id)
                )
        # if host start or stop
        elif command_type == 'HOSTTARGET':
            if hasattr(self, 'on_start_host') or \
               hasattr(self, 'on_stop_host'):
                channel_name = command[2][1:]
                try:
                    channel = self._channels_by_name[channel_name]
                # if doesn't exist
                except KeyError:
                    self._delayed_msgs.setdefault(channel_name, []).append(irc_message)
                    return
                hoster, viewers_count = text.split(' ', 1)
                if viewers_count == '-':
                    viewers_count = 0
                else:
                    viewers_count = int(viewers_count)
                # start
                try:
                    if hoster != '-' and hasattr(self, 'on_start_host'):
                        self._do_later(
                            self.on_start_host(channel, viewers_count, hoster)
                        )
                    # stop
                    elif hoster == '-' and hasattr(self, 'on_stop_host'):
                        self._do_later(
                            self.on_stop_host(channel, viewers_count)
                        )
                    else:
                        raise UnknownHostTarget(irc_message)
                except ValueError as e:
                    print('\n!!!\n'
                          f'{type(e)}\n'
                          f'{irc_message}\n'
                          f'{command}\n'
                          f'!!!\n')
        # if reconnecting request
        elif command_type == 'RECONNECT':
            for channel_name in self._channels_by_name:
                self._do_later(self._send(f'JOIN #{channel_name.lower()}'))
        # if room join or room update
        elif command_type == 'ROOMSTATE':
            channel_id = tags['room-id']
            room_info_length = 7  # room join
            room_update_length = 2  # room_update
            # if room join
            if len(tags) == room_info_length:
                channel_name = command[2][1:]
                my_state_tags = self._local_states_tags.pop(channel_name)
                # create channel
                channel = Channel(channel_name, my_state_tags, self._ws, tags)
                self._channels_by_id[channel_id] = channel
                self._channels_by_name[channel_name] = channel
                # do later delayed messages
                delayed_msgs = self._delayed_msgs.pop(channel_name, [])
                while delayed_msgs:
                    irc_message = delayed_msgs.pop(0)
                    self._do_later(self._handle_message(irc_message))
                # event handle
                if hasattr(self, 'on_room_join'):
                    self._do_later(
                        self.on_room_join(self._channels_by_id[channel_id])
                    )
            # if room update
            elif len(tags) == room_update_length:
                tags.pop('room-id')  # need to only one key for the next row
                key, value = tags.popitem()
                # event handle
                if hasattr(self, 'on_room_update'):
                    channel = self._channels_by_id[channel_id]
                    # before
                    before = copy(channel)
                    before.nameslist = copy(channel.nameslist)
                    # update
                    channel.update(key, value)
                    # after
                    after = copy(channel)
                    after.nameslist = copy(channel.nameslist)
                    self._do_later(
                        self.on_room_update(self._channels_by_id[channel_id], before, after)
                    )
                # if hasn't handler
                else:
                    channel = self._channels_by_id[channel_id]
                    channel.update(key, value)
            # if anything else
            else:
                raise UnknownRoomState(irc_message)  # we must not recive others ROOMSTATEs
        # if our local state
        elif command_type == 'USERSTATE':
            channel_name = command[2][1:]
            self._local_states_tags[channel_name] = tags
        # if our global state
        elif command_type == 'GLOBALUSERSTATE':
            self.global_state = Client.GlobalState(tags)
            if hasattr(self, 'on_login'):  # if even registered - call it
                self._do_later(self.on_login())
        elif command_type == 'CAP':
            return
        else:
            raise UnknownCommand(irc_message)

    @staticmethod
    async def _parse_message(
            message: str
    ) -> Tuple[Dict[str, str], List[str], Optional[str]]:
        # if hasn't tags
        if message.startswith(':'):
            raw_parts = message.split(':', 2)
        # if has tags
        elif message.startswith('@'):
            raw_parts = message.split(' :', 2)
        # never anything else
        else:
            raise InvalidMessageStruct(message)
        # raws
        # if with text
        if len(raw_parts) == 3:
            raw_tags, raw_command, text = raw_parts
        # if without text
        elif len(raw_parts) == 2:
            raw_tags, raw_command = raw_parts
            text = ''
        # never other length
        else:
            raise InvalidMessageStruct(message)
        # tags
        tags = parse_raw_tags(raw_tags[1:])  # remove @ in the start
        # command
        command = raw_command.split(' ')
        return tags, command, text

    def _handle_nameslist_part(self, tags: dict, command: list, text: str):
        channel_name = command[4][1:].lower()
        nameslist_part = text.split(' ')  # current part
        channel_nameslist = self._channels_nameslists.setdefault(channel_name, [])
        channel_nameslist.extend(nameslist_part)

    def _handle_nameslist_end(self, tags: dict, command: list, text: str):
        channel_name = command[4][1:].lower()
        try:
            channel = self._channels_by_name[channel_name]
        # if doesn't exist
        except KeyError:
            raise TooEarlyMessage
        else:
            channel_nameslist = self._channels_nameslists[channel_name]
            channel.nameslist = tuple(channel_nameslist)

    def _handle_notice(self, tags: dict, command: list, text: str):
        notice_id = tags['msg-id']
        if notice_id == 'msg_room_not_found':
            raise InvalidChannelName(f'Channel with name: "{command[2]}" is not found!')

    def _handle_roominfo(self, tags: dict, command: list, text: str):
        channel_id = tags['room-id']
        channel_name = command[2][1:]
        my_state_tags = self._local_states_tags.pop(channel_name)
        # create channel
        channel = Channel(channel_name, my_state_tags, self._ws, tags)
        self._channels_by_id[channel_id] = channel
        self._channels_by_name[channel_name] = channel
        # do delayed messages
        delayed_msgs = self._delayed_msgs.pop(channel_name, [])
        while delayed_msgs:
            irc_message = delayed_msgs.pop(0)
            self._do_later(
                self._handle_message(irc_message)
            )

    def _handle_roomupdate(self, tags: dict, command: list, text: str):
        channel_id = tags['room-id']
        tags.pop('room-id')  # needed only one key for the next code-row
        key, value = tags.popitem()
        # update
        channel = self._channels_by_id[channel_id]
        channel.update(key, value)

    def _handle_userstate(self, tags: dict, command: list, text: str):
        pass

    def _handle_globaluserstate(self, tags: dict, command: list, text: str):
        pass

    async def _send(self, command: str):
        await self._ws.send(command + '\r\n')

    async def send_msg(self, channel: Union[int, str, Channel], text: str):
        if type(channel) == Channel:
            channel = channel.name
        elif type(channel) == int:
            channel = self._channels_by_id[channel].name
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
        if coro.__name__ in Client.events_names:
            setattr(self, coro.__name__, coro)
            return coro
        # if user event
        elif coro.__name__ in Client.user_events_names:
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
            self.id = tags['user-id']
