import asyncio
from copy import copy
from asyncio import iscoroutinefunction, get_event_loop, AbstractEventLoop
from websockets import connect, WebSocketClientProtocol, ConnectionClosedError

from errors import *
from irc_user_events import *
from irc_message import Message
from irc_whisper import Whisper
from irc_member import Member
from irc_channel import Channel, LocalState
from utils import parse_raw_tags, parse_raw_badges

from typing import Coroutine, Iterable, Tuple, Union, Any, Awaitable, Callable, List, Optional


__all__ = (
    'Client',
    'GlobalState'
)


class Client:
    """

    """
    _user_events_types: Dict[str, Tuple[str, Any]] = {
        # msg_id: (handler_name, event_class)
        'sub': ('on_sub', Sub),
        'resub': ('on_resub', ReSub),
        'subgift': ('on_sub_gift', SubGift),
        'submysterygift': ('on_sub_mistery_gift', SubMysteryGift),
        'primepaidupgrade': ('on_prime_paid_upgrade', PrimePaidUpgrade),
        'giftpaidupgrade': ('on_gift_paid_upgrade', GiftPaidUpgrade),
        'anongiftpaidupgrade': ('on_gift_paid_upgrade', GiftPaidUpgrade),
        'standardpayforward': ('on_standard_pay_forward', StandardPayForward),
        'communitypayforward': ('on_community_pay_forward', CommunityPayForward),
        'bitsbadgetier': ('on_bits_badge_tier', BitsBadgeTier),
        'ritual': ('on_ritual', Ritual),
        'raid': ('on_raid', Raid),
        'unraid': ('on_unraid', UnRaid)
    }

    events_handler_names = (
        'on_message',  # PRIVMSG
        'on_whisper',  # WHISPER
        'on_channel_update', 'on_self_join',  # ROOMSTATE
        'on_my_state_update',  # USERSTATE
        'on_nameslist_update',  # 366
        'on_login',  # GLOBALUSERSTATE
        'on_join',  # JOIN
        'on_left',  # PART
        'on_clear_user', 'on_clear_chat',  # CLEARCHAT
        'on_message_delete',  # CLEARMSG
        'on_start_host', 'on_stop_host',  # HOSTTARGET
        'on_notice', 'on_join_error',  # NOTICE
        'on_user_event', 'on_unknown_user_event'  # USERNOTICE
    )

    user_event_handler_names = (
        'on_sub', 'on_resub', 'on_sub_gift',  'on_sub_mistery_gift',  # subs
        'on_prime_paid_upgrade', 'on_gift_paid_upgrade',  # upgrades
        'on_standard_pay_forward', 'on_community_pay_forward',  # payments forward
        'on_bits_badge_tier',  # bits badges tier
        'on_reward_gift',  # rewards
        'on_raid', 'on_unraid',  # raids
        'on_ritual'  # rituals
    )

    def __init__(
            self,
            token: str,
            login: str,
            *,
            should_restart: bool = True,
            whisper_channel_login: str = None
    ) -> None:
        # channels
        self.joined_channels_logins: set = set()
        self._channels_by_id: Dict[str, Channel] = {}  # dict of id_channel: Channel
        self._channels_by_login: Dict[str, Channel] = {}  # dict of channel_login : Channel
        self._unprepared_channels: Dict[str, Channel] = {}  # unprepared channels by login
        # unprotected
        self.token: str = token
        self.login: str = login
        self.loop: AbstractEventLoop = get_event_loop()
        self.should_restart: bool = should_restart
        self.whisper_channel_login: Optional[str] = whisper_channel_login
        self.global_state: Optional[GlobalState] = None
        # protected
        self._websocket: Optional[WebSocketClientProtocol] = None
        # channels prepare things
        self._delayed_irc_parts: Dict[str, List[Tuple[Dict, List, str]]] = {}
        self._channels_nameslists: Dict[str, Union[List[str], Tuple[str]]] = {}
        self._local_states: Dict[str, LocalState] = {}

    #################################
    # getters and properties
    #
    def get_channel_by_id(
            self,
            channel_id: str,
            default: Any = None
    ) -> Union[Channel, Any]:
        """Returns :class:`Channel` by id if exists else - `default`"""
        return self._channels_by_id.get(channel_id, default)

    def get_channel_by_login(
            self,
            channel_login: str,
            default: Any = None
    ) -> Union[Channel, Any]:
        """Returns :class:`Channel` by login if exists else - `default`"""
        return self._channels_by_login.get(channel_login, default)

    def _get_channel_if_exists(
            self,
            channel_login: str
    ) -> Channel:
        """
        returns channel with given login if exists, else raises ChannelNotExists

        Args:
            channel_login: `str`
                login of channel that want to be received

        Returns:
            Channel
        """
        try:
            return self._channels_by_login[channel_login]
        except KeyError:
            raise ChannelNotExists(channel_login)
    #
    # end of getters and properties
    #################################

    def run(
            self,
            channels: Iterable[str]
    ) -> None:
        """
        Starts event listener, use this if you want to start 'Client' as a single worker.

        Notes:
            If you want to start `Client` with any other async code - look 'start()'

        Args:
            channels: Iterable[`str`]
                Iterable object with logins of channel to join
        """
        self.loop.run_until_complete(
            self.start(channels)
        )

    async def connect_irc(
            self,
            channels: Iterable[str]
    ) -> None:
        """Creates new websocket connection and send all login's commands"""

        uri: str = 'wss://irc-ws.chat.twitch.tv:443'
        self._websocket = await connect(uri)
        # capability
        await self._send('CAP REQ :twitch.tv/membership')
        await self._send('CAP REQ :twitch.tv/commands')
        await self._send('CAP REQ :twitch.tv/tags')
        # loging
        await self._send(f'PASS {self.token}')
        await self._send(f'NICK {self.login}')
        # joining
        self.joined_channels_logins = set(channels)
        self._do_later(self.join_channels(channels))

    async def reconnect_irc(self):
        """reconnect websocket and irc with channels from `self.joined_channels_logins`"""
        await self.connect_irc(self.joined_channels_logins)

    async def _read_websocket(self):
        """tries read websocket, and restarts irc if connection is closed"""
        while True:
            # try read
            try:
                irc_messages = await self._websocket.recv()
            # if websocket is closed
            except ConnectionClosedError:
                if self.should_restart:
                    await self.reconnect_irc()
            # if no exeptions
            else:
                for irc_message in irc_messages.split('\r\n'):
                    # if empty
                    if not irc_message:
                        continue
                    # if PING
                    elif irc_message.startswith('PING'):
                        await self._send('PONG :tmi.twitch.tv')
                    # others
                    else:
                        yield self._parse_irc_message(irc_message)  # tags, command, text

    async def start(
            self,
            channels: Iterable[str]
    ) -> None:
        """
        |Coroutine|
        Starts event listener.

        Notes:
            If you won't combine this with any other async code - you can use sync method 'self.run()'.

        Args:
            channels: |Iterable[str]|
                Iterable object with logins of channel to join
        """

        async def try_log_in():
            """tries to log"""
            await self.connect_irc(channels)
            async for tags, command, text in self._read_websocket():
                # if successful login
                if command[1] == 'GLOBALUSERSTATE':
                    self.global_state = GlobalState(self.login, tags)
                    # if has handler
                    if hasattr(self, 'on_login'):
                        self._do_later(self.on_login())
                    return
                # if logging error
                elif command[1] == 'NOTICE' and command[-1] == '*':
                    raise InvalidToken(text)
                # if a command that we don't expect
                elif command[1] not in ('001', '002', '003', '004', '372', '375', '376', 'CAP'):
                    return

        # try log in
        await try_log_in()
        # start main listener
        async for tags, command, text in self._read_websocket():
            self._do_later(self._select_handler(tags, command, text))

    @staticmethod
    def _parse_irc_message(
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
            raise InvalidMessageStruct(message)  # must be no other length
        tags = parse_raw_tags(raw_tags)
        command = raw_command.split(' ')
        return tags, command, text

    async def _select_handler(self, tags, command, text) -> None:
        command_type = command[1]
        # if message in a channel
        try:
            # if message in chat
            if command_type == 'PRIVMSG':
                self._handle_privmsg(tags, command, text)
            elif command_type == 'WHISPER':
                self._handle_whisper(tags, command, text)
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
                self._handle_usernotice(tags, command, text)
            # if `clear chat` or `clear user`
            elif command_type == 'CLEARCHAT':
                self._handle_clearchat(tags, command, text)
            # if message delete
            elif command_type == 'CLEARMSG':
                self._handle_clearmsg(tags, command, text)
            # if host start or host stop
            elif command_type == 'HOSTTARGET':
                self._handle_hosttarget(command, text)
            # if part of namelist of a channel
            elif command_type == '353':
                self._handle_nameslist_part(command, text)
            # if end of nameslist
            elif command_type == '366':
                self._handle_nameslist_end(command)
            # if room join or room update
            elif command_type == 'ROOMSTATE':
                self._handle_roomstate(tags, command)
            # if our local state
            elif command_type == 'USERSTATE':
                self._handle_userstate(tags, command)
            # if our global state
            elif command_type == 'GLOBALUSERSTATE':
                self.global_state = GlobalState(self.login, tags)

            elif command_type == 'RECONNECT': # still don't know what this is, but let's reconnct to all channels.
                self._do_later(self.join_channels(self.joined_channels_logins))
        except ChannelNotExists:
            channel_login = command[-1][1:]
            await self._delay_this_message((tags, command, text), channel_login)

    #################################
    # channels prepare handlers
    #
    def _handle_nameslist_part(self, command: list, text: str):
        channel_login = command[-1][1:]
        nameslist_part = text.split(' ')  # current part
        nameslist = self._channels_nameslists.setdefault(channel_login, [])
        nameslist.extend(nameslist_part)

    def _handle_nameslist_end(self, command: list):
        channel_login = command[-1][1:]
        nameslist = self._channels_nameslists.pop(channel_login)
        # if prepared
        if channel_login in self._channels_by_login:
            channel = self._channels_by_login[channel_login]
            # if has handler
            if hasattr(self, 'on_nameslist_update'):
                before = channel.nameslist
                channel.nameslist = tuple(nameslist)
                after = channel.nameslist
                self._do_later(
                    self.on_nameslist_update(channel, before, after)
                )
            # if has not handler
            else:
                channel.nameslist = tuple(nameslist)
        # if unprepared
        elif channel_login in self._unprepared_channels:
            channel = self._unprepared_channels[channel_login]
            channel.nameslist = tuple(nameslist)
            # save if ready
            if self._is_channel_ready(channel_login):  # isn't ready if isn't in unprepared
                self._save_channel(channel_login)
        # if not exists
        else:
            self._channels_nameslists[channel_login] = tuple(nameslist)  # save for set it later

    def _handle_roomstate(self, tags: dict, command: list):
        channel_login = command[-1][1:]
        # if exists
        if channel_login in self._channels_by_login:
            self._handle_channel_update(tags, command)
        elif channel_login in self._unprepared_channels:
            self._handle_channel_update(tags, command)
        # if not exists
        else:
            self._handle_new_channel(tags, command)

    def _handle_new_channel(self, tags, command):
        channel_login = command[-1][1:]
        # create channel
        channel = Channel(channel_login, self._send, tags)
        # insert my_state if exists
        channel.my_state = self._local_states.pop(channel_login, None)
        # insert nameslist if exists
        nameslist = self._channels_nameslists.get(channel_login)
        if type(nameslist) == tuple:
            channel.nameslist = nameslist
            self._channels_nameslists.pop(channel_login)  # remove
        # save channel as unprepared
        self._unprepared_channels[channel_login] = channel
        # save as prepared if ready
        if self._is_channel_ready(channel_login):
            self._save_channel(channel_login)

    def _handle_channel_update(self, tags, command):
        channel_login = command[-1][1:]
        channel = self._channels_by_login.get(channel_login)
        # if channel is prepared
        if channel is not None:
            # if has handler
            if hasattr(self, 'on_channel_update'):
                before = copy(channel)
                channel.set_new_values(tags)
                after = copy(channel)
                self._do_later(
                    self.on_channel_update(before, after)
                )
            # if hasn't handler
            else:
                channel.set_new_values(tags)
        # if channel is not prepared
        elif channel_login in self._unprepared_channels:
            channel = self._unprepared_channels[channel_login]
            channel.set_new_values(tags)

    def _handle_userstate(self, tags: dict, command: list):
        channel_login = command[-1][1:]
        # if prepared
        if channel_login in self._channels_by_login:
            channel = self._channels_by_login[channel_login]
            # if has handler
            if hasattr(self, 'on_my_state_update'):
                before = channel.my_state
                channel.my_state = LocalState(tags)
                after = channel.my_state
                self._do_later(
                    self.on_my_state_update(channel, before, after)
                )
            # if hasn't handler
            else:
                channel.my_state = LocalState(tags)
        # if unprepared
        elif channel_login in self._unprepared_channels:
            channel = self._unprepared_channels[channel_login]
            channel.my_state = LocalState(tags)
            if self._is_channel_ready(channel_login):
                self._save_channel(channel_login)
        # if not exists
        else:
            self._local_states[channel_login] = LocalState(tags)

    def _is_channel_ready(self, channel_login) -> bool:
        """
        Returns True if channel with `channel_login` is ready:
            1. it in `self._unprepared_channels`
            2. has localstate - `channel.my_state`
            3. has nameslist - `channel.nameslist`

        Args:
            channel_login: `str`
                login of channel to checking

        Returns:
            `bool`, if channel with `channel_login` is ready
        """
        channel = self._unprepared_channels.get(channel_login)
        if channel is None:
            return False
        if type(channel.my_state) != LocalState:
            return False
        if type(channel.nameslist) != tuple:
            return False
        else:
            return True

    def _save_channel(self, channel_login: str):
        """
        1. Removes channel from `self._unprepared_channels`
        2. Puts it in `self._channels_by_id` and `self._channels_by_login`
        3. Creates async task `on_self_join`
        4. Creates async tasks that will handle every delayed message
        Args:
            channel_login:
                login of channel to save

        Returns:
            `None`
        """
        channel = self._unprepared_channels.pop(channel_login)
        self._channels_by_id[channel.id] = channel
        self._channels_by_login[channel_login] = channel
        # if has handler
        if hasattr(self, 'on_self_join'):
            self._do_later(
                self.on_self_join(channel)
            )
        # handle delayed irc_messages
        delayed_irc_parts = self._delayed_irc_parts.pop(channel_login, [])
        for delayed_irc_part in delayed_irc_parts:
            self._do_later(
                self._select_handler(*delayed_irc_part)  # unpack the parts as tags, command, text
            )
    #
    # end of: channels prepare methods
    #################################

    #################################
    # handlers
    #
    def _handle_privmsg(self, tags: dict, command: List[str], text: str):
        if hasattr(self, 'on_message'):
            channel_login = command[-1][1:]
            channel = self._get_channel_if_exists(channel_login)
            if 'login' not in tags:
                tags['login'] = command[0].split('!', 1)[0]
            author = Member(channel, tags)
            message = Message(channel, author, text, tags)
            # if has hadler
            self._do_later(
                self.on_message(message)
            )

    def _handle_whisper(self, tags: dict, command: List[str], text: str):
        if hasattr(self, 'on_whisper'):
            if 'user-login' not in tags:
                tags['user-login'] = command[0].split('!', 1)[0]
            whisper = Whisper(tags, text, self.send_whisper)
            self._do_later(
                self.on_whisper(whisper)
            )

    def _handle_join(self, command: list):
        if hasattr(self, 'on_join'):
            channel_login = command[-1][1:]
            channel = self._get_channel_if_exists(channel_login)
            user_login = command[0].split('!', 1)[0]
            # if has hadler
            self._do_later(
                self.on_join(channel, user_login)
            )

    def _handle_part(self, command: list):
        if hasattr(self, 'on_left'):
            user_login = command[0].split('!', 1)[0]
            channel_login = command[-1][1:]
            channel = self._get_channel_if_exists(channel_login)
            # if has hadler
            self._do_later(
                self.on_left(channel, user_login)
            )

    def _handle_notice(self, tags: dict, command: list, text: str):
        notice_id = tags.get('msg-id')
        # if channel join error
        if notice_id == 'msg_room_not_found':
            channel_login = command[-1][1:]
            self.joined_channels_logins.discard(channel_login)
            if hasattr(self, 'on_self_join_error'):
                self._do_later(
                    self.on_self_join_error(channel_login)
                )
        elif hasattr(self, 'on_notice'):
            channel_login = command[-1][1:]
            channel = self._get_channel_if_exists(channel_login)
            # if has hadler
            self._do_later(
                self.on_notice(channel, notice_id, text)
            )

    def _handle_clearchat(self, tags, command, text):
        # if clear user
        if text:
            if hasattr(self, 'on_clear_user'):
                # channel
                channel_login = command[-1][1:]
                channel = self._get_channel_if_exists(channel_login)
                # values
                target_user_login = text
                ban_duration = int(tags.get('ban-duration', 0))
                taget_message_id = tags.get('ban-duration')
                taget_user_id = tags.get('ban-duration')
                # handle later
                self._do_later(
                    self.on_clear_user(channel, target_user_login, taget_user_id, taget_message_id, ban_duration)
                )
        # if clear chat
        else:
            if hasattr(self, 'on_clear_chat'):
                channel_login = command[-1][1:]
                channel = self._get_channel_if_exists(channel_login)
                # if has hadler
                self._do_later(
                    self.on_clear_chat(channel)
                )

    def _handle_clearmsg(self, tags, command, text):
        if hasattr(self, 'on_message_delete'):
            # channel
            channel_login = command[-1][1:]
            channel = self._get_channel_if_exists(channel_login)
            # values
            user_login = tags.get('login')
            message_id = tags.get('target-msg-id')
            time = int(tags.get('tmi-sent-ts', '0'))
            # handle later
            self._do_later(
                self.on_message_delete(channel, user_login, text, message_id, time)
            )

    def _handle_usernotice(self, tags: dict, command: list, text: str):
        # channel
        channel_login = command[-1][1:]
        channel = self._get_channel_if_exists(channel_login)
        # select handler
        event_type = tags.get('msg-id')
        try:
            event_attr_name, event_class = Client._user_events_types[event_type]
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
            if hasattr(self, event_attr_name):
                author = Member(channel, tags)
                event_handler = getattr(self, event_attr_name)  # get the handler by its name
                event = event_class(author, channel, text, tags)
                self._do_later(event_handler(event))
            # if has global handler
            elif hasattr(self, 'on_user_event'):
                author = Member(channel, tags)
                event = event_class(author, channel, text, tags)
                self._do_later(
                    self.on_user_event(event)
                )

    def _handle_hosttarget(self, command: list, text: str):
        if hasattr(self, 'on_start_host') or hasattr(self, 'on_stop_host'):
            channel_login = command[-1][1:]
            channel = self._get_channel_if_exists(channel_login)
            # values
            hoster_login, viewers_count = text.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else 0
            # if start
            if hoster_login != '-' and hasattr(self, 'on_start_host'):
                self._do_later(
                    self.on_start_host(channel, viewers_count, hoster_login)
                )
            # if stop
            elif hoster_login == '-' and hasattr(self, 'on_stop_host'):
                self._do_later(
                    self.on_stop_host(channel, viewers_count)
                )
    #
    # end of: handlers
    #################################

    #################################
    # IRC commands
    #
    async def _send(
            self,
            command: str
    ) -> None:
        """
        Sends raw message in websocket

        Args:
            command: `str`
                command to send

        Returns:
            `None`
        """
        await self._websocket.send(command + '\r\n')

    async def send_message(
            self,
            channel_login: str,
            content: str
    ) -> None:
        """
        Sends `content` into the channel with login equals `channel_login`

        Args:
            channel_login: `str`
                login of channel into which the `content` should be sent.
            content: `str`
                content to send into the channel

        Returns:
            `None`
        """
        await self._send(f'PRIVMSG #{channel_login} :{content}')

    async def send_whisper(
            self,
            recipient_login: str,
            conntent: str,
            *,
            via_channel: str = None
    ) -> None:
        """
        Sends whisper with `content` to the recipient with login equals `recipient_login`

        Args:
            recipient_login: `str`
                login of recipient
            conntent: `str`
                content to send
            via_channel: `str`
                login of channel via which the whisper would be sent

        Returns:
            `None`
        """
        conntent = rf'/w {recipient_login} {conntent}'
        # if specified channel for the whisper
        if via_channel is not None:
            via_channel = via_channel
        # if specified channel for a whisper
        elif self.whisper_channel_login is not None:
            via_channel = self.whisper_channel_login
        # if not specified
        else:
            via_channel = self.login
        # send
        await self.send_message(via_channel, conntent)

    async def join_channel(
            self,
            login: str
    ) -> None:
        """Sends command to join the channel and adds its login to `self.joined_channels_logins`"""
        await self._send(f'JOIN #{login}')
        self.joined_channels_logins.add(login)

    async def join_channels(
            self,
            logins: Iterable[str],
            *,
            timeout: float = 20,
            ignore_exceptions: bool = True
    ) -> None:
        """
        Sends commands to join the channels and adds their logins to `self.joined_channels_logins`

        Args:
            logins: Iterable[`str`]
                Iterable object with logins of channel
            timeout: `float` (default: 20.0)
                time for send all commands, if out of it - cancel all unfinished
            ignore_exceptions: `bool`
                marks if should ignore all exceptions (e.g. )

        Returns:
            `None`
        """
        awaitables = [self.join_channel(login) for login in logins]
        try:
            # wait for all tasks
            await asyncio.wait_for(
                asyncio.gather(*awaitables),
                timeout=timeout
            )
        except:
            if not ignore_exceptions:
                raise

    async def part_channel(
            self,
            login: str
    ) -> None:
        """Sends command to part the channel and discards its login from `self.joined_channels_logins`"""
        await self._send(f'PART #{login}')
        self.joined_channels_logins.discard(login)

    async def part_channels(
            self,
            logins: Iterable[str],
            *,
            timeout: float = 20,
            ignore_exceptions: bool = True
    ) -> None:
        """
        Sends commands to part the channels and discards their logins from `self.joined_channels_logins`

        Args:
            logins: Iterable[`str`]
                Iterable object with logins of channel
            timeout: `float` (default: 20.0)
                time for send all commands, if out of it - cancel all unfinished
            ignore_exceptions: `bool`
                marks if should ignore all exceptions (e.g. )

        Returns:
            `None`
        """
        awaitables = [self.part_channel(login) for login in logins]
        try:
            # wait for all tasks
            await asyncio.wait_for(
                asyncio.gather(*awaitables),
                timeout=timeout
            )
        except:
            if not ignore_exceptions:
                raise
    #
    # end of: IRC commands
    #################################

    #################################
    # event's things
    #

    def event(self, coro: Coroutine) -> Coroutine:
        """
        |DECORATOR|
        registers handler of event

        Args:
            coro: Coroutine
                an Coroutine that will be called when the event would be happened, should has known name of event

        Raises:
            errors.UnknownEvent
                if got unknown name of event
            errors.FunctionIsNotCorutine
                if object is not Coroutine

        Returns:
            Coroutine:
                the object that the method got in `coro` as argument
        """
        self._register_event(coro.__name__, coro)
        return coro
    
    def events(self, *handlers_names: str) -> Callable:
        """
        returns |DECORATOR|
        registers handler of events. use as a decorator.

        Examples:
            1st:
                1. >>>> ttv_bot = Client(token='', login='')
                2. >>>> @ttv_bot.events('on_sub', 'on_resub')
                3. >>>> async def any_name_of_handler(event):
                4. >>>> ....pass
            2nd:
                1. >>>> events = ('on_sub', 'on_resub')
                2. >>>> ttv_bot = Client(token='', login='')
                3. >>>> @ttv_bot.events(*events)
                4. >>>> async def any_name_of_handler(event):
                5. >>>> ....pass

        Args:
            handlers_names: Iterable[`str`]
                names of events that must be registered

        Raises:
        ================
            errors.UnknownEvent
                if got unknown name of event
            errors.FunctionIsNotCorutine
                if object is not Coroutine
        ----------------

        Returns:
        ================
            Coroutine:
                the object that the method got in `coro`-argument
        ----------------
        """
        def decorator(coro: Coroutine) -> Coroutine:
            for handler_name in handlers_names:
                self._register_event(handler_name, coro)
            return coro
        # prepared decorator would be returned
        return decorator

    def _register_event(
            self,
            handler_name: str,
            coro: Coroutine
    ) -> None:
        """
        1. Registers event with given name.
        2. Checks that the `coro` is Coroutine.
        3. Checks that the `handler_name` is known.

        Args:
            handler_name: `str`
                name of handler, should be known
            coro: Coroutine
                this would be called when a event registered as `handler_name` happen.

        Returns:
            `None`
        """
        # if event
        if not iscoroutinefunction(coro):
            raise FunctionIsNotCorutine(coro.__name__)
        if handler_name in Client.events_handler_names:
            setattr(self, handler_name, coro)
        # if user event
        elif handler_name in Client.user_event_handler_names:
            setattr(self, handler_name, coro)
        else:  # what for a developer will register unknown event? better tell him/her about
            raise UnknownEvent(f'Unknown event name{handler_name}')
    #
    # end of: event's things
    #################################

    def _do_later(
            self,
            coro: Awaitable
    ) -> None:
        """Creates a async task in `self.loop`"""
        self.loop.create_task(coro)

    async def _delay_this_message(
            self,
            parts: Tuple[dict, list, str],
            channel_login: str
    ) -> None:
        """
        Delays the `parts`(as parts of irc_message).\n
        Delayed messages will be handled after the channel with `channel_login` is created

        Args:
            parts: Tuple[dict, list, str]
                parts of irc_message to delay
            channel_login: `str`
                login of the channel, after creation of which the message must be handled

        Returns:
            `None`
        """
        delayed_parts = self._delayed_irc_parts.setdefault(channel_login, [])
        if len(delayed_parts) == 10:
            # something wrong if we've delayed 10 messages, let's try to reconnect to the channel
            await self.join_channel(channel_login)
            print('Try to rejoin')
            delayed_parts.append(parts)
        # protection from memory overflow
        elif len(delayed_parts) >= 30:
            pass
        else:
            delayed_parts.append(parts)


class GlobalState:
    """
    Object of the class would contains information about global state of `Client`

    Attrs:
        self.login: `str`
            login of `Client`
        self.display_name: `str`
            display name of `Client`
        self.id: `str`
            id of `Client`
        self.color: `str`
            nick-name color of `Client`
        self.emote_sets: Tuple[`str`]
            Tuple with id of emote-sets that `Client` owns
        self.badges: Dict[`str`, `str`]
            badges of `Client`
        self.badge_info: Dict[`str`, `str`]
            additional information of badges of `Client`
    """
    def __init__(self, login, tags: Dict[str, str]):
        """

        Args:
            login: `str`
                login of `Client`
            tags: Dict[`str`, `str`]
                prepared tags from irc_message
        """
        # prepared
        self.login = login
        # badges
        self.badges: Dict[str, str] = parse_raw_badges(tags.get('badges', ''))
        self.badge_info: Dict[str, str] = parse_raw_badges(tags.get('badge-info', ''))
        # stable tags
        self.color: str = tags.get('color')
        self.display_name: str = tags.get('display-name')
        self.emote_sets: Tuple[str] = tuple(tags.get('emote-sets', '').split(','))
        self.id: str = tags.get('user-id')
