from copy import copy
from typing import Coroutine, Iterable, Tuple, Union, Any, Awaitable, Callable
from asyncio import get_event_loop
from asyncio.coroutines import iscoroutinefunction
from websockets import connect, WebSocketClientProtocol

from abcs import StateABC
from errors import *
from irc_user_events import *
from irc_message import Message
from irc_member import Member
from irc_channel import Channel, LocalState
from utils import parse_raw_tags

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
        'on_channel_update', 'on_self_join',  # ROOMSTATE
        'on_login',  # GLOBALUSERSTATE
        'on_join',  # JOIN
        'on_left',  # PART
        'on_clear_user', 'on_clear_chat',  # CLEARCHAT
        'on_message_delete',  # CLEARMSG
        'on_start_host', 'on_stop_host',  # HOSTTARGET
        'on_notice', 'on_join_error',  # NOTICE
        'on_user_event', 'on_unknown_user_event'  # USERNOTICE
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
        self._unprepared_channels: Dict[str, Channel] = {}  # unprepared channels by name
        # non-protected
        self.loop = get_event_loop()
        self.global_state: Optional[GlobalState] = None
        # protected
        self._ws: Optional[WebSocketClientProtocol] = None
        # prepare things
        self._delayed_irc_parts: Dict[str, List[Tuple[Dict, List, str]]] = {}
        self._local_states_tags: Dict[str, Dict[str, str]] = {}
        self._channels_nameslists: Dict[str, Union[List[str], Tuple[str]]] = {}

    #################################
    # getters and properties
    #
    def get_channel_by_id(self, channel_id: str, default: Any = None):
        return self._channels_by_id.get(channel_id, default)

    def get_channel_by_name(self, channel_name: str, default: Any = None):
        return self._channels_by_name.get(channel_name, default)
    #
    # end of getters and properties
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
        channels = list(channels)  # we'll modify this
        for channel in channels:
            self._do_later(self._send(f'JOIN #{channel.lower()}'))
        # handling loop
        while True:
            irc_messages = await self._ws.recv()
            for irc_message in irc_messages.split('\r\n'):
                if len(irc_message) == 0:
                    pass
                elif irc_message.startswith('PING'):
                    self._do_later(self._send('PONG :tmi.twitch.tv'))
                else:
                    tags, command, text = await self._parse_irc_message(irc_message)
                    self._do_later(self._handle_message(tags, command, text))

    async def _handle_message(self, tags, command, text) -> None:
        command_type = command[1]
        # if message in a channel
        try:
            if command_type == 'PRIVMSG':
                self._handle_privmsg(tags, text)
            # if join
            elif command_type == 'JOIN':
                self._handle_join(command)
            # if leave
            elif command_type == 'PART':
                self._handle_part(command)
            # if NOTICE
            elif command_type == 'NOTICE':
                self._handle_notice(tags, command, text)
            # if user event
            elif command_type == 'USERNOTICE':
                self._handle_user_event(tags, command, text)
            # if `clear chat` or `clear user`
            elif command_type == 'CLEARCHAT':
                self._handle_clearchat(tags, command, text)
            # if message delete
            elif command_type == 'CLEARMSG':
                self._handle_clearmsg(tags, command, text)
            # if host start or host stop
            elif command_type == 'HOSTTARGET':
                if hasattr(self, 'on_start_host') or hasattr(self, 'on_stop_host'):
                    self._handle_hosttarget(command, text)
            # if part of namelist of a channel
            elif command_type == '353':
                self._handle_nameslist_part(command, text)
            # if end of nameslist
            elif command_type == '366':
                self._handle_nameslist_end(command)
            # if room join or room update
            elif command_type == 'ROOMSTATE':
                if len(tags) == 7:  # new channel
                    self._handle_new_channel(tags, command)
                elif len(tags) == 2:  # channel update
                    self._handle_channel_update(tags, command)
            # if our local state
            elif command_type == 'USERSTATE':
                self._handle_userstate(tags, command)
            # if our global state
            elif command_type == 'GLOBALUSERSTATE':
                self.global_state = GlobalState(tags)
                # if has handler
                if hasattr(self, 'on_login'):
                    self._do_later(self.on_login())
            # if reconnect request
            elif command_type == 'RECONNECT':
                print('\n\nRECONNECT\nWhat the fuck!?\n\n')
                print('tags=', tags, '\n',
                      'command =', command, '\n',
                      'text =', text)
                channels_names = self._channels_by_name.keys()
                for channel_name in channels_names:
                    self._do_later(self._send(f'JOIN #{channel_name.lower()}'))
        except ChannelNotExists as e:
            channel_name = e.args[0]
            parts = (tags, command, text)
            self._delay_this_message(parts, channel_name)

    @staticmethod
    async def _parse_irc_message(
            message: str
    ) -> Tuple[Dict[str, str], List[str], Optional[str]]:
        raw_parts = message[1:].split(' :', 2)  # remove ':' or '@' in start of the irc_message
        # if hasn't tags
        if message.startswith(':'):
            raw_parts.insert(0, '')  # easier to insert empty raw_tags than to make logic
        # if has text
        if len(raw_parts) == 3:
            raw_tags, raw_command, text = raw_parts
        # if hasn't text
        elif len(raw_parts) == 2:
            raw_tags, raw_command = raw_parts
            text = ''
        else:
            raise InvalidMessageStruct(message)  # must not be other length
        tags = parse_raw_tags(raw_tags)
        command = raw_command.split(' ')
        return tags, command, text

    #################################
    # channels prepare methods
    #
    def _handle_nameslist_part(self, command: list, text: str):
        channel_name = command[-1][1:].lower()
        nameslist_part = text.split(' ')  # current part
        nameslist = self._channels_nameslists.setdefault(channel_name, [])
        nameslist.extend(nameslist_part)

    def _handle_nameslist_end(self, command: list):
        channel_name = command[-1][1:].lower()
        channel = self._unprepared_channels.get(channel_name)
        nameslist = self._channels_nameslists.pop(channel_name)
        if channel is None:
            print('NAMESLIST before channel #', channel_name, sep='')
            self._channels_nameslists[channel_name] = tuple(nameslist)  # save for insert later
        else:
            print('NAMESLIST after channel #', channel_name, sep='')
            channel.nameslist = tuple(nameslist)  # insert into the channel
            # save if ready
            if self._is_channel_ready(channel_name):
                self._save_channel(channel_name)

    def _handle_new_channel(self, tags: dict, command: list):
        channel_name = command[-1][1:]
        # create channel
        channel = Channel(channel_name, self._ws, tags)
        # insert my_state if exists
        my_state_tags = self._local_states_tags.pop(channel_name, None)
        if my_state_tags is not None:
            channel.my_state = LocalState(my_state_tags)
        # insert nameslist if exists
        nameslist = self._channels_nameslists.pop(channel_name, None)
        if type(nameslist) == tuple:
            channel.nameslist = nameslist
        # save channel
        self._unprepared_channels[channel_name] = channel
        # save if ready
        if self._is_channel_ready(channel_name):
            self._save_channel(channel_name)

    def _handle_channel_update(self, tags: dict, command: list):
        channel_name = command[-1][1:]
        tags.pop('room-id')  # we need to the only one `key` in the next code-row
        new_key, new_value = tags.popitem()  # here only one item after previous `pop`
        channel = self._channels_by_name.get(channel_name)
        # if channel is unprepared
        if channel is None:
            channel = self._unprepared_channels[channel_name]
            channel.update(new_key, new_value)
        # if channel is prepared
        else:
            # if has handler
            if hasattr(self, 'on_channel_update'):
                before = copy(channel)
                channel.update(new_key, new_value)
                after = copy(channel)
                self._do_later(
                    self.on_channel_update(before, after)
                )
            # if hasn't handler
            else:
                channel.update(new_key, new_value)

    def _handle_userstate(self, tags: dict, command: list):
        channel_name = command[-1][1:]
        channel = self._channels_by_name.get(channel_name)
        # if channel exists
        if channel is not None:
            channel.mystate = LocalState(tags)
        # if channel not exists
        else:
            self._local_states_tags[channel_name] = tags
        # save if ready
        if self._is_channel_ready(channel_name):
            self._save_channel(channel_name)

    def _is_channel_ready(self, channel_name) -> bool:
        channel = self._unprepared_channels.get(channel_name)
        if channel is None:
            return False
        if type(channel.my_state) != LocalState:
            return False
        if type(channel.nameslist) != tuple:
            return False
        else:
            return True

    def _save_channel(self, channel_name: str):
        channel = self._unprepared_channels.pop(channel_name)
        channel_id = channel.id
        self._channels_by_id[channel_id] = channel
        self._channels_by_name[channel_name] = channel
        # if has handler
        if hasattr(self, 'on_self_join'):
            self._do_later(
                self.on_self_join(channel)
            )
        # handle delayed irc_messages
        delayed_irc_parts = self._delayed_irc_parts.pop(channel_name, [])
        for delayed_irc_part in delayed_irc_parts:
            self._do_later(
                self._handle_message(*delayed_irc_part)  # unpack the parts as tags, command, text
            )
    #
    # end of: channels prepare methods
    #################################

    #################################
    # handlers
    #
    def _handle_privmsg(self, tags: dict, text: str):
        if hasattr(self, 'on_message'):
            channel_id = tags['room-id']
            channel = self._channels_by_id[channel_id]
            author = Member(channel, tags)
            message = Message(channel, author, text, tags)
            self._do_later(
                self.on_message(message)
            )

    def _handle_join(self, command: list):
        if hasattr(self, 'on_join'):
            channel_name = command[-1][1:]
            try:
                channel = self._channels_by_name[channel_name]
            # if doesn't exist
            except KeyError:
                raise ChannelNotExists(channel_name)
            # if exist
            else:
                user_name = command[0].split('!', 1)[0]
                self._do_later(
                    self.on_join(channel, user_name)
                )

    def _handle_part(self, command: list):
        if hasattr(self, 'on_left'):
            user_name = command[0].split('!', 1)[0]
            channel_name = command[-1][1:]
            channel = self._channels_by_name[channel_name]
            self._do_later(
                self.on_left(channel, user_name)
            )

    def _handle_notice(self, tags: dict, command: list, text: str):
        notice_id = tags['msg-id']
        if notice_id == 'msg_room_not_found':
            if hasattr(self, 'on_self_join_error'):
                channel_name = command[-1][1:]
                self.on_self_join_error(channel_name)
        elif hasattr(self, 'on_notice'):
            channel_name = command[-1][1:]
            channel = self._channels_by_name.get(channel_name)
            # if channel exists
            if channel is not None:
                self._do_later(
                    self.on_notice(channel, notice_id, text)
                )
            # if channel not exists
            else:
                raise ChannelNotExists(channel_name)

    def _handle_clearchat(self, tags, command, text):
        # if clear user
        if text is not None and hasattr(self, 'on_clear_user'):
            channel_name = command[-1][1:]
            channel = self._channels_by_name[channel_name]
            user_name = text
            ban_duration = tags.get('ban-duration')
            if ban_duration is not None:
                ban_duration = int(ban_duration)
            self._do_later(
                self.on_clear_user(channel, user_name, ban_duration)
            )
        # if clear chat
        elif hasattr(self, 'on_clear_chat'):
            channel_name = command[-1][1:]
            channel = self._channels_by_name[channel_name]
            self._do_later(
                self.on_clear_chat(channel)
            )

    def _handle_clearmsg(self, tags, command, text):
        if hasattr(self, 'on_message_delete'):
            channel_name = command[-1][1:]
            channel = self._channels_by_name[channel_name]
            user_name = tags['login']
            message_id = tags['target-msg-id']
            self._do_later(
                self.on_message_delete(channel, user_name, text, message_id)
            )

    def _handle_user_event(self, tags: dict, command: list, text: str):
        channel_id = tags['room-id']
        channel = self._channels_by_id.get(channel_id)
        if channel is None:
            channel_name = command[-1][1:]
            raise ChannelNotExists(channel_name)
        # main variables
        author = Member(channel, tags)
        event_type = tags['msg-id']
        # defining event type
        try:
            event_attr, event_class = Client._user_events_types[event_type]
        # if unknown event
        except KeyError:
            if hasattr(self, 'on_unknown_user_event'):
                self._do_later(
                    self.on_unknown_user_event(tags, command, text)
                )
            return
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

    def _handle_hosttarget(self, command: list, text: str):
        channel_name = command[-1][1:]
        try:
            channel = self._channels_by_name[channel_name]
        # if channel not exists
        except KeyError:
            raise ChannelNotExists(channel_name)
        hoster, viewers_count = text.split(' ', 1)
        if viewers_count == '-':
            viewers_count = 0
        else:
            viewers_count = int(viewers_count)
        if hoster != '-' and hasattr(self, 'on_start_host'):
            self._do_later(
                self.on_start_host(channel, viewers_count, hoster)
            )
        # stop
        elif hoster == '-' and hasattr(self, 'on_stop_host'):
            self._do_later(
                self.on_stop_host(channel, viewers_count)
            )
    #
    # end of: handlers
    #################################

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

    def _do_later(self, coro: Awaitable):
        self.loop.create_task(coro)

    def _delay_this_message(self, parts: Tuple[dict, list, str], channel_name: str):
        """
        Delays the `parts` from args as parts of irc_message.\n
        Delayed messages will be handled after the channel with `channel_name` is created

        ----------------

        Args:
        ================
            message: `str`
                irc_message to delay
            channel_name: `str`
                name of the channel, after the creation of which the message must be handled
        ----------------

        Returns:
        ================
            None
        ----------------
        """
        delayed_messages = self._delayed_irc_parts.setdefault(channel_name, [])
        delayed_messages.append(parts)

    def events(self, handlers_names: Iterable[str]) -> Callable:
        def decorator(coro: Coroutine) -> Coroutine:
            print('decorator was called')
            for handler_name in handlers_names:
                if handler_name in Client.events_names:
                    setattr(self, handler_name, coro)
                # if user event
                elif handler_name in Client.user_events_names:
                    setattr(self, handler_name, coro)
                # if unknown
                else:
                    # what for a developer will register unknown event? better tell him/her about
                    raise UnknownEvent(handler_name)
            return coro

        return decorator

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


class GlobalState(StateABC):
    def __init__(self, tags):
        super().__init__(tags)
        self.color = tags['color']
        self.name = tags['display-name']
        self.emotes = tuple(map(int, tags['emote-sets'].split(',')))
        self.id = tags['user-id']
