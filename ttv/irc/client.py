import asyncio
from asyncio import iscoroutinefunction, get_event_loop, AbstractEventLoop
import websockets
from websockets import WebSocketClientProtocol, ConnectionClosedError, ConnectionClosedOK
from copy import copy
from time import time

from .irc_message import IRCMessage
from .messages import ChannelMessage, WhisperMessage
from .channel import Channel
from .users import ChannelMember, GlobalUser
from .user_states import GlobalState, LocalState
from .events import ClearChatFromUser
from .user_events import *
from .exceptions import *

from typing import Coroutine, Iterable, Tuple, Union, Any, Awaitable, Callable, List, Optional, Dict, AsyncGenerator, \
    Set, Generator

__all__ = (
    'Client',
)


class Client:

    def __init__(
            self,
            token: str,
            login: str,
            *,
            should_restart: bool = True,
            whisper_agent: str = None
    ) -> None:
        # channels
        self.joined_channel_logins: Set[str] = set()
        self._channels_by_id: Dict[str, Channel] = {}  # id_channel: Channel
        self._channels_by_login: Dict[str, Channel] = {}  # channel_login: Channel
        self._unprepared_channels: Dict[str, Channel] = {}  # channel_login: unprepared_channel
        self._nameslists: Dict[str, Union[List[str], Tuple[str]]] = {}  # channel_login: nameslists
        self._local_states: Dict[str, LocalState] = {}  # channel_login: local_state
        self._delayed_irc_msgs: Dict[str, List[IRCMessage]] = {}  # channel_login: [irc_msg, ...]
        # unprotected
        self.token: str = token
        self.login: str = login
        self.is_running = False
        self.should_restart: bool = should_restart
        self.whisper_agent: Optional[str] = whisper_agent
        self.global_state: Optional[GlobalState] = None
        self.loop: AbstractEventLoop = get_event_loop()
        # protected
        self._websocket: WebSocketClientProtocol = WebSocketClientProtocol()
        self._delay_gen: Generator[int, None] = Client._delay_gen()

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value: str):
        if not value.startswith('oauth:'):
            value = 'oauth:' + value
        self._token = value

    def get_channel_by_id(
            self,
            channel_id: str,
            default: Any = None
    ) -> Channel:
        """Returns :class:`Channel` by id if exists else - `default`"""
        return self._channels_by_id.get(channel_id, default)

    def get_channel_by_login(
            self,
            login: str,
            default: Any = None
    ) -> Channel:
        """Returns :class:`Channel` by login if exists else - `default`"""
        return self._channels_by_login.get(login, default)

    def _get_prepared_channel(
            self,
            login: str
    ) -> Channel:
        """
        returns channel with given login if exists, else raises ChannelNotExists

        Args:
            login: `str`
                login of channel that must be returned

        Returns:
            Channel
        """
        try:
            return self._channels_by_login[login]
        except KeyError:
            raise ChannelNotExists(login)

    @classmethod
    def _delay_gen(cls) -> Generator[int, None, None]:
        delay = 0
        while True:
            last_delayed = time()
            yield delay
            # increase
            delay = min(16, max(1, delay * 2))  # if 0 - then 1, no greater then 16
            # reset
            if time() - last_delayed > 60:
                delay = 0  # resetting overwrites increasing

    def run(
            self,
            channels: Iterable[str]
    ) -> None:
        """
        Starts event listener, use this if you want to start 'Client' as a single worker.

        Notes:
            If you want to start `Client` with another async code - look 'start()'

        Args:
            channels: Iterable[`str`]
                Iterable object with logins of channel to join
        """
        self.loop.run_until_complete(
            self.start(channels)
        )

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
            channels: (Iterable[str])
                Iterable object with logins of channel to join
        """
        # try log in
        await self._first_log_in_irc()
        await self.join_channels(channels)
        # start main listener
        self.is_running = True
        async for irc_msg in self._read_websocket():
            self._do_later(self._handle_command(irc_msg))  # protection from a shut down caused by an exception
        self.is_running = False

    async def restart(self):
        """
        1. Reopens websocket connection if not open.
        2. Relogin into twitch IRC
        3. Rejoins(joins) channel from `self.joined_channels_logins`
        4. Calls `self.on_reconnect` event handler if registered.
        """
        delay = self._delay_gen.__next__()
        await asyncio.sleep(delay)
        await self._log_in_irc()
        await self.join_channels(self.joined_channel_logins)
        if hasattr(self, 'on_reconnect'):
            self._do_later(self.on_reconnect())

    async def _first_log_in_irc(
            self,
            *,
            expected_commands: Iterable[str] = ('001', '002', '003', '004', '372', '375', '376', 'CAP')
            ):
        await self._log_in_irc()
        async for irc_msg in self._read_websocket():
            # if successfully logged in
            if irc_msg.command == 'GLOBALUSERSTATE':
                if 'user-login' not in irc_msg.tags:
                    irc_msg.tags['user-login'] = self.login
                self.global_state = GlobalState(irc_msg.tags)
                # if has handler
                if hasattr(self, 'on_login'):
                    self._do_later(self.on_login())
                return
            elif irc_msg.command == 'NOTICE' and irc_msg.params[0] == '*':
                raise LoginFailed(irc_msg.content)
            elif irc_msg.command == 'CAP' and irc_msg.params[1] == 'NAK':
                raise CapabilitiesReqError(irc_msg)
            elif irc_msg.command not in expected_commands:
                return

    async def _log_in_irc(
            self,
            *,
            uri: str = 'wss://irc-ws.chat.twitch.tv:443'
    ):
        """Creates new websocket connection if not open, requires capabilities and login into twitch IRC"""
        if not self._websocket.open:
            self._websocket = await websockets.connect(uri)
            # capabilities
            await self._send('CAP REQ :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
            # loging
            await self._send(f'PASS {self.token}')
            await self._send(f'NICK {self.login}')

    async def _read_websocket(
            self
    ) -> AsyncGenerator[IRCMessage, None]:
        """
        tries to read websocket:
            1. if successfully read: yields tags, command, parsed irc_msg;
            2. if `websockets.ConnectionClosedError`: reconnects irc if `self.should_restart`.
        also handles PING requests.
        """
        while True:
            try:
                raw_irc_messages = await self._websocket.recv()
            except ConnectionClosedOK:
                return
            # if websocket is closed
            except ConnectionClosedError:
                if self.should_restart:
                    await self.restart()
                else:
                    raise
            # if successfully read
            else:
                for raw_irc_message in raw_irc_messages.split('\r\n'):
                    if raw_irc_message:  # might be empty
                        yield IRCMessage(raw_irc_message)

    async def _handle_command(
            self,
            irc_msg: IRCMessage
    ) -> None:
        try:
            handler = self._command_hanldes[irc_msg.command]
        except KeyError:
            if hasattr(self, 'on_unknown_command'):
                self.on_unknown_command(irc_msg)
        else:
            try:
                handler(self, irc_msg)
            except ChannelNotExists:
                channel_login = irc_msg.middles[-1][1:]
                await self._delay_irc_message(irc_msg, channel_login)

    def _handle_nameslist_part(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel_login = irc_msg.middles[-1][1:]
        nameslist_part = irc_msg.content.split(' ')  # current part
        nameslist = self._nameslists.setdefault(channel_login, [])
        nameslist.extend(nameslist_part)

    def _handle_nameslist_end(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel_login = irc_msg.middles[-1][1:]
        # if prepared
        if channel_login in self._channels_by_login:
            self._handle_nameslist_update(irc_msg)
        # if unprepared
        elif channel_login in self._unprepared_channels:
            self._handle_new_nameslist(irc_msg)
        # if not exists
        else:
            nameslist = self._nameslists.pop(channel_login)
            self._nameslists[channel_login] = tuple(nameslist)  # save for set it later

    def _handle_nameslist_update(
            self,
            irc_msg: IRCMessage
    ):
        channel_login = irc_msg.middles[-1][1:]
        channel = self._channels_by_login[channel_login]
        nameslist = self._nameslists.pop(channel_login)
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

    def _handle_new_nameslist(
            self,
            irc_msg: IRCMessage
    ):
        channel_login = irc_msg.middles[-1][1:]
        nameslist = self._nameslists.pop(channel_login)
        channel = self._unprepared_channels[channel_login]
        channel.nameslist = tuple(nameslist)
        # save if ready
        if self._is_channel_ready(channel_login):  # isn't ready if isn't in unprepared
            self._save_channel(channel_login)

    def _handle_roomstate(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel_login = irc_msg.middles[-1][1:]
        if 'room-login' not in irc_msg.tags:
            irc_msg.tags['room-login'] = channel_login
        # if exists
        if channel_login in self._channels_by_login or channel_login in self._unprepared_channels:
            self._handle_channel_update(irc_msg)
        # if not exists
        else:
            self._handle_new_channel(irc_msg)

    def _handle_new_channel(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel_login = irc_msg.middles[-1][1:]
        channel = Channel(irc_msg.tags, self._send)
        channel.my_state = self._local_states.pop(channel_login, None)
        # nameslist
        nameslist = self._nameslists.get(channel_login)
        if type(nameslist) == tuple:
            channel.nameslist = nameslist
            self._nameslists.pop(channel_login)  # remove
        # save channel as unprepared
        self._unprepared_channels[channel_login] = channel
        # save as prepared if ready
        if self._is_channel_ready(channel_login):
            self._save_channel(channel_login)

    def _handle_channel_update(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel_login = irc_msg.middles[-1][1:]
        channel = self._channels_by_login.get(channel_login)
        # if channel is prepared
        if channel is not None:
            # if has handler
            if hasattr(self, 'on_channel_update'):
                before = copy(channel)
                channel.update_values(irc_msg.tags)
                after = copy(channel)
                self._do_later(
                    self.on_channel_update(before, after)
                )
            # if hasn't handler
            else:
                channel.update_values(irc_msg.tags)
        # if channel is not prepared
        elif channel_login in self._unprepared_channels:
            channel = self._unprepared_channels[channel_login]
            channel.update_values(irc_msg.tags)

    def _handle_userstate(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel_login = irc_msg.middles[-1][1:]
        if 'user-login' not in irc_msg.tags:
            irc_msg.tags['user-login'] = self.global_state.login
        if 'user-id' not in irc_msg.tags:
            irc_msg.tags['user-id'] = self.global_state.id
        # if prepared
        if channel_login in self._channels_by_login:
            self._handle_userstate_update(irc_msg)
        # if unprepared
        elif channel_login in self._unprepared_channels:
            self._handle_new_userstate(irc_msg)
        # if not exists
        else:
            self._local_states[channel_login] = LocalState(irc_msg.tags)

    def _handle_userstate_update(
            self,
            irc_msg: IRCMessage
    ):
        channel_login = irc_msg.middles[-1][1:]
        channel = self._channels_by_login[channel_login]
        # if has handler
        if hasattr(self, 'on_my_state_update'):
            before = channel.my_state
            channel.my_state = LocalState(irc_msg.tags)
            after = channel.my_state
            self._do_later(
                self.on_my_state_update(channel, before, after)
            )
        # if hasn't handler
        else:
            channel.my_state = LocalState(irc_msg.tags)

    def _handle_new_userstate(
            self,
            irc_msg: IRCMessage
    ):
        channel_login = irc_msg.middles[-1][1:]
        channel = self._unprepared_channels[channel_login]
        channel.my_state = LocalState(irc_msg.tags)
        if self._is_channel_ready(channel_login):
            self._save_channel(channel_login)

    def _handle_privmsg(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_message'):
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            if 'user-login' not in irc_msg.tags:
                irc_msg.tags['user-login'] = irc_msg.nickname
            author = ChannelMember(irc_msg.tags, channel, self.send_whisper)
            message = ChannelMessage(channel, author, irc_msg.content, irc_msg.tags)
            # if has hadler
            self._do_later(
                self.on_message(message)
            )

    def _handle_whisper(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_whisper'):
            if 'user-login' not in irc_msg.tags:
                irc_msg.tags['user-login'] = irc_msg.nickname
            author = GlobalUser(irc_msg.tags, self.send_whisper)
            whisper = WhisperMessage(author, irc_msg.content, irc_msg.tags)
            self._do_later(
                self.on_whisper(whisper)
            )

    def _handle_join(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_join'):
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            user_login = irc_msg.nickname
            # if has hadler
            self._do_later(
                self.on_join(channel, user_login)
            )

    def _handle_part(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_part'):
            user_login = irc_msg.nickname
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            # if has hadler
            self._do_later(
                self.on_part(channel, user_login)
            )

    def _handle_notice(
            self,
            irc_msg: IRCMessage
    ) -> None:
        notice_id = irc_msg.tags.get('msg-id')
        # if channel join error
        if notice_id == 'msg_room_not_found':
            channel_login = irc_msg.middles[-1][1:]
            self.joined_channel_logins.discard(channel_login)
            if hasattr(self, 'on_self_join_error'):
                self._do_later(
                    self.on_self_join_error(channel_login)
                )
        elif hasattr(self, 'on_notice'):
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            # if has hadler
            self._do_later(
                self.on_notice(channel, notice_id, irc_msg.content)
            )

    def _handle_clearchat(
            self,
            irc_msg: IRCMessage
    ) -> None:
        # if clear user
        if irc_msg.content:  # text contains login of the user
            self._handle_clear_chat_from_user(irc_msg)
        # if clear chat
        else:
            self._handle_clear_chat(irc_msg)

    def _handle_clear_chat_from_user(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_clear_chat_from_user'):
            # channel
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            # values
            target_user_login = irc_msg.content
            taget_user_id = irc_msg.tags.get('target-user-id')
            taget_message_id = irc_msg.tags.get('target-msg-id')
            ban_duration = int(irc_msg.tags.get('ban-duration', 0))
            # handle later
            self._do_later(
                self.on_clear_chat_from_user(
                    channel,
                    ClearChatFromUser(target_user_login, taget_user_id, taget_message_id, ban_duration)
                )
            )

    def _handle_clear_chat(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_clear_chat'):
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            # if has hadler
            self._do_later(
                self.on_clear_chat(channel)
            )

    def _handle_clearmsg(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_message_delete'):
            # channel
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            # values
            user_login = irc_msg.tags.get('login')
            message_id = irc_msg.tags.get('target-msg-id')
            tmi_time = int(irc_msg.tags.get('tmi-sent-ts', '0'))
            # handle later
            self._do_later(
                self.on_message_delete(channel, user_login, irc_msg.content, message_id, tmi_time)
            )

    def _handle_usernotice(
            self,
            irc_msg: IRCMessage
    ) -> None:
        # channel
        channel_login = irc_msg.middles[-1][1:]
        channel = self._get_prepared_channel(channel_login)
        # select handler
        event_type = irc_msg.tags.get('msg-id')
        try:
            event_name, event_class = self._USER_EVENT_TYPES[event_type]
        # if unknown event
        except KeyError:
            if hasattr(self, 'on_unknown_user_event'):
                self._do_later(
                    self.on_unknown_user_event(irc_msg)
                )
            return
        # if known event
        else:
            # if has specified event handler
            if hasattr(self, event_name):
                author = ChannelMember(irc_msg.tags, channel, self.send_whisper)
                event_handler = getattr(self, event_name)  # get the handler by its name
                event = event_class(author, channel, irc_msg.content, irc_msg.tags)
                self._do_later(event_handler(event))
            # if has global handler
            elif hasattr(self, 'on_user_event'):
                author = ChannelMember(irc_msg.tags, channel, self.send_whisper)
                event = event_class(author, channel, irc_msg.content, irc_msg.tags)
                self._do_later(
                    self.on_user_event(event)
                )

    def _handle_hosttarget(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_host_start') or hasattr(self, 'on_host_stop'):
            hoster_login, viewers_count = irc_msg.content.split(' ', 1)
            if hoster_login == '-':
                self._hanlde_host_start(irc_msg)
            else:
                self._hanlde_host_stop(irc_msg)

    def _hanlde_host_start(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_host_start'):
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            hoster_login, viewers_count = irc_msg.content.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else 0
            self._do_later(
                self.on_host_start(channel, viewers_count, hoster_login)
            )

    def _hanlde_host_stop(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_host_stop'):
            channel_login = irc_msg.middles[-1][1:]
            channel = self._get_prepared_channel(channel_login)
            hoster_login, viewers_count = irc_msg.content.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else 0
            self._do_later(
                self.on_host_stop(channel, viewers_count)
            )

    def _handle_globaluserstate(
            self,
            irc_msg: IRCMessage
    ):
        if 'user-login' not in irc_msg.tags:
            irc_msg.tags['user-login'] = self.login
        if hasattr(self, 'on_global_state_update'):
            before = self.global_state
            self.global_state = GlobalState(irc_msg.tags)
            after = self.global_state
            self._do_later(
                self.on_global_state_update(before, after)
            )
        else:
            self.global_state = GlobalState(irc_msg.tags)

    def _handle_reconnect(
            self,
            irc_msg: IRCMessage
    ):
        self._do_later(self.restart())

    def _handle_ping(
            self,
            irc_msg: IRCMessage
    ):
        self._do_later(self._send('PONG :tmi.twitch.tv'))

    def _is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        """
        Returns True if channel with `channel_login` is ready:
            1. is in `self._unprepared_channels`
            2. has localstate (`channel.my_state`)
            3. has nameslist (`channel.nameslist`)

        Args:
            channel_login: `str`
                login of channel to check

        Returns:
            `bool`, indicates if channel with `channel_login` is ready
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

    def _save_channel(
            self,
            channel_login: str
    ) -> None:
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
        delayed_irc_messages = self._delayed_irc_msgs.pop(channel_login, [])
        for delayed_irc_message in delayed_irc_messages:
            self._do_later(
                self._handle_command(delayed_irc_message)
            )

    async def _send(
            self,
            irc_message: str
    ) -> None:
        """
        Sends raw irc message through websocket connection

        Args:
            irc_message: `str`
                command to send

        Returns:
            `None`
        """
        while True:
            try:
                await self._websocket.send(irc_message + '\r\n')  # TODO: check does it work
            except websockets.ConnectionClosed:
                if self.should_restart:
                    await self.restart()
                else:
                    raise
            else:
                break

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
            target: str,
            content: str,
            *,
            agent: str = None
    ) -> None:
        """
        Sends whisper with `content` to the recipient with login equals `recipient_login`

        Args:
            target: `str`
                login of recipient
            content: `str`
                content to send
            agent: `str`
                login of channel via which the whisper must be sent

        Returns:
            `None`
        """
        # if specified agent for the whisper
        if agent is not None:
            agent = agent
        # if specified agent for a whisper
        elif self.whisper_agent is not None:
            agent = self.whisper_agent
        # if not specified
        else:
            agent = self.login
        # send
        content = rf'/w {target} {content}'
        await self.send_message(agent, content)

    async def join_channel(
            self,
            login: str
    ) -> None:
        """Sends command to join the channel and adds its login to `self.joined_channels_logins`"""
        self.joined_channel_logins.add(login)
        await self._send(f'JOIN #{login}')

    async def join_channels(
            self,
            logins: Iterable[str]
    ) -> None:
        """
        Sends commands to join the channels and adds their logins to `self.joined_channels_logins`

        Args:
            logins: Iterable[`str`]
                Iterable object with channels' logins

        Returns:
            `None`
        """
        if logins:
            self.joined_channel_logins.update(logins)
            logins_str = ',#'.join(logins)
            await self._send(f'JOIN #{logins_str}')

    async def part_channel(
            self,
            login: str
    ) -> None:
        """Sends command to part the channel and discards its login from `self.joined_channels_logins`"""
        self.joined_channel_logins.discard(login)
        await self._send(f'PART #{login}')

    async def part_channels(
            self,
            logins: Iterable[str]
    ) -> None:
        """
        Sends commands to part the channels and discards their logins from `self.joined_channels_logins`

        Args:
            logins: Iterable[`str`]
                Iterable object with channels' logins

        Returns:
            `None`
        """
        if logins:
            self.joined_channel_logins.difference_update(logins)
            logins_str = ',#'.join(logins)
            await self._send(f'PART #{logins_str}')

    def event(self, coro: Callable[[], Coroutine]) -> Callable[[], Coroutine]:
        """
        |DECORATOR|
        registers handler of event

        Args:
            coro: Coroutine
                a Coroutine that will be called when the event would be happened, should has known name of event

        Raises:
            errors.UnknownEvent
                if got unknown event's name
            errors.FunctionIsNotCorutine
                if `coro` is not Coroutine

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

        Args:
            *handlers_names: str
                names of events that must be registered

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

        Raises:
            errors.UnknownEvent
                if got unknown name of event
            errors.FunctionIsNotCorutine
                if object is not Coroutine

        Returns:
            Coroutine:
                the object that the method got in `coro`-argument
        """
        def decorator(coro: Callable[[], Coroutine]) -> Callable[[], Coroutine]:
            for handler_name in handlers_names:
                self._register_event(handler_name, coro)
            return coro
        # prepared decorator would be returned
        return decorator

    def _register_event(
            self,
            handler_name: str,
            coro: Callable[[], Coroutine]
    ) -> None:
        """
        1. Registers event with given name.
        2. Checks that the `coro` is Coroutine.
        3. Checks that the `handler_name` is known.

        Args:
            handler_name: `str`
                name of handler, should be known
            coro: Coroutine
                coroutine that must hundle specified event.

        Returns:
            `None`
        """
        if not iscoroutinefunction(coro):
            raise FunctionIsNotCorutine(coro.__name__)
        # if event
        if handler_name in self.EVENTS:
            setattr(self, handler_name, coro)
        # if user event
        elif handler_name in self.USER_EVENTS:
            setattr(self, handler_name, coro)
        else:  # what for a developer will register unknown event? better tell that person about
            raise UnknownEvent(handler_name)

    async def _delay_irc_message(
            self,
            irc_msg: IRCMessage,
            channel_login: str
    ) -> None:
        """
        Delays `irc_msg`.
        Delayed message will be handled after the channel with `channel_login` is created

        Args:
            irc_msg: `IRCMessage`
                `IRCMessage` to delay
            channel_login: `str`
                login of the channel, after creation of which the message must be handled

        Returns:
            `None`
        """
        delayed_irc_messages = self._delayed_irc_msgs.setdefault(channel_login, [])
        if len(delayed_irc_messages) == 10:
            # something's wrong if there are 10 delayed messages, better reconnect
            await self.join_channel(channel_login)
            print(f'Try to rejoin #{channel_login}')  # TODO: modify the print into logging
            delayed_irc_messages.append(irc_msg)
        # protection from memory overflow
        elif len(delayed_irc_messages) == 30:
            print(f'#{channel_login} has delayed msgs overflow')  # TODO: modify the print into logging
            delayed_irc_messages.append(irc_msg)
        elif len(delayed_irc_messages) > 30:
            pass
        else:
            delayed_irc_messages.append(irc_msg)

    def _do_later(
            self,
            coro: Awaitable
    ) -> None:
        """Creates an async task in `self.loop`"""
        self.loop.create_task(coro)

    _command_hanldes: Dict[str, Callable[[Any, IRCMessage], Any]] = {
        'PRIVMSG': _handle_privmsg,
        'WHISPER': _handle_whisper,
        'JOIN': _handle_join,
        'PART': _handle_part,
        'NOTICE': _handle_notice,
        'USERNOTICE': _handle_usernotice,
        'CLEARCHAT': _handle_clearchat,
        'CLEARMSG': _handle_clearmsg,
        'HOSTTARGET': _handle_hosttarget,
        'ROOMSTATE': _handle_roomstate,
        'USERSTATE': _handle_userstate,
        'GLOBALUSERSTATE': _handle_globaluserstate,
        'RECONNECT': _handle_reconnect,
        'PING': _handle_ping,
        '353': _handle_nameslist_part,
        '366': _handle_nameslist_end
    }

    _USER_EVENT_TYPES: Dict[str, Tuple[str, Any]] = {
        # event_type(or 'msg-id'): (event_handler, event_class)
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

    EVENTS = (
        'on_message',  # PRIVMSG
        'on_whisper',  # WHISPER
        'on_channel_update', 'on_self_join',  # ROOMSTATE
        'on_my_state_update',  # USERSTATE
        'on_nameslist_update',  # 366
        'on_login', 'on_global_state_update',  # GLOBALUSERSTATE
        'on_join',  # JOIN
        'on_part',  # PART
        'on_clear_chat_from_user', 'on_clear_chat',  # CLEARCHAT
        'on_message_delete',  # CLEARMSG
        'on_host_start', 'on_host_stop',  # HOSTTARGET
        'on_notice', 'on_join_error',  # NOTICE
        'on_user_event', 'on_unknown_user_event',  # USERNOTICE
        'on_reconnect', 'on_unknown_command', 'on_self_join_error'
    )

    USER_EVENTS = (
        'on_sub', 'on_resub', 'on_sub_gift', 'on_sub_mistery_gift',  # subs
        'on_prime_paid_upgrade', 'on_gift_paid_upgrade',  # upgrades
        'on_standard_pay_forward', 'on_community_pay_forward',  # payments forward
        'on_bits_badge_tier',  # bits badges tier
        'on_reward_gift',  # rewards
        'on_raid', 'on_unraid',  # raids
        'on_ritual'  # rituals
    )
