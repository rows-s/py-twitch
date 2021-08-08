import asyncio
from asyncio import iscoroutinefunction, AbstractEventLoop
import websockets
from websockets import WebSocketClientProtocol, ConnectionClosedError, ConnectionClosedOK
from time import time

from .irc_message import IRCMessage
from .messages import ChannelMessage, Whisper
from .channel import Channel, ChannelsAccumulator
from .users import ChannelUser, GlobalUser
from .user_states import GlobalState, LocalState
from .events import OnClearChatFromUser, OnChannelJoinError, OnNotice, OnMessageDelete, OnSendMessageError
from .user_events import *
from .exceptions import *

from typing import Coroutine, Iterable, Tuple, Any, Awaitable, Callable, List, Optional, Dict, AsyncGenerator, \
    Set, Generator, TypeVar

__all__ = ('Client', 'ANON_LOGIN')


ANON_LOGIN = 'justinfan0'


_Client = TypeVar('_Client')


class Client:

    def __init__(  # TODO: add `should_accum_names`, then remove `AnonChannelsAccumulator`
            self,
            token: str,
            login: str,
            *,
            whisper_agent: str = 'ananonymousgifter',
            should_restart: bool = True,
            # accumulation
            should_accum_client_states=True,
            should_accum_names=False,
            should_accum_commands=False,
            should_accum_vips=False,
            should_accum_mods=False,
            loop: AbstractEventLoop = None
    ) -> None:
        self.token: str = token
        self.login: str = login
        # state
        self.is_running = False
        self.whisper_agent: str = whisper_agent
        self.should_restart: bool = should_restart
        self.global_state: Optional[GlobalState] = None
        # channels
        self.joined_channel_logins: Set[str] = set()
        self._channels_by_id: Dict[str, Channel] = {}
        self._channels_by_login: Dict[str, Channel] = {}
        self._delayed_irc_msgs: Dict[str, List[IRCMessage]] = {}  # channel_login: [irc_msg, ...]
        self._channels_accumulator = ChannelsAccumulator(
            channel_ready_callback=self._save_channel,
            send_callback=self._send,
            should_accum_client_states=should_accum_client_states,
            should_accum_names=should_accum_names,
            should_accum_commands=should_accum_commands,
            should_accum_mods=should_accum_mods,
            should_accum_vips=should_accum_vips,
        )
        self._websocket: WebSocketClientProtocol = WebSocketClientProtocol()
        self._delay_gen: Generator[int, None] = Client._delay_gen()
        self._running_restart_task: Optional[asyncio.tasks.Task] = None
        self.loop: AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, value: str):
        if not value:
            pass
        elif not value.startswith('oauth:'):
            value = 'oauth:' + value
        self._token = value

    @property
    def is_restarting(self) -> bool:
        return self._running_restart_task is not None

    @property
    def should_accum_client_states(self) -> bool:
        return self._channels_accumulator.should_accum_client_states

    @property
    def should_accum_names(self) -> bool:
        return self._channels_accumulator.should_accum_names

    @property
    def should_accum_commands(self) -> bool:
        return self._channels_accumulator.should_accum_commands

    @property
    def should_accum_mods(self) -> bool:
        return self._channels_accumulator.should_accum_mods

    @property
    def should_accum_vips(self) -> bool:
        return self._channels_accumulator.should_accum_vips

    @property
    def is_anon(self) -> bool:
        return self.login.startswith('justinfan') and not self.login == 'justinfan'

    def get_channel(
            self,
            login_or_id: str,
            default: Any = None
    ) -> Channel:
        """
        Returns :cls:`Channel`:
            1: by login if exists
            2: by id if exists
            3: default
        """
        try:
            return self._channels_by_login[login_or_id]
        except KeyError:
            return self._channels_by_id.get(login_or_id, default)

    def get_channel_by_id(
            self,
            channel_id: str,
            default: Any = None
    ) -> Channel:
        """Returns :cls:`Channel` by id if exists else - :arg:`default`"""
        return self._channels_by_id.get(channel_id, default)

    def get_channel_by_login(
            self,
            login: str,
            default: Any = None
    ) -> Channel:
        """Returns :cls:`Channel` by id if exists else - :arg:`default`"""
        return self._channels_by_login.get(login, default)

    def _get_prepared_channel(
            self,
            login: str
    ) -> Channel:
        """
        returns :class:`Channel` with given login if exists, else raises :exc:`ChannelNotPrepared`

        Args:
            login :class:`str`: login of the channel that must be returned
        """
        try:
            return self._channels_by_login[login]
        except KeyError:
            raise ChannelNotPrepared(login)

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
        Starts event listener.

        Args:
            channels Iterable[`str`] : Object with logins of channels to join

        Notes:
            Async version of the method is :meth:`start`
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
        if not self.is_anon:
            await self._first_log_in_irc()
        else:
            await self._log_in_irc()
        await self.join_channels(channels)
        self.is_running = True
        async for irc_msg in self._read_websocket():
            self._do_later(
                self._handle_command(irc_msg)  # protection from a shutdown caused by an exception
            )
        self.is_running = False

    async def restart(self):
        """
        1. Reopens websocket connection if not open.
        2. Relogin into twitch IRC
        3. Rejoins(joins) channel from `self.joined_channels_logins`
        4. Calls `self.on_reconnect` event if registered.
        """
        self._running_restart_task = asyncio.create_task(self._restart())
        await self._running_restart_task

    async def _restart(self):
        delay = next(self._delay_gen)
        await asyncio.sleep(delay)
        await self._log_in_irc()
        await self.join_channels(self.joined_channel_logins)
        self._call_event('on_reconnect')
        self._running_restart_task = None

    async def stop(self):  # TODO: script for case: self.is_running == False
        self.is_running = False
        await self._websocket.close()

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
                self.global_state = GlobalState(irc_msg)
                # if has handler
                self._call_event('on_ready')
                return
            elif irc_msg.command == 'NOTICE' and irc_msg.middles[0] == '*':
                raise LoginFailed(irc_msg.trailing)
            elif irc_msg.command == 'CAP' and irc_msg.middles[1] == 'NAK':
                raise CapReqError(irc_msg)
            elif irc_msg.command not in expected_commands:
                return

    async def _log_in_irc(
            self,
            *,
            uri: str = 'wss://irc-ws.chat.twitch.tv:443'
    ):
        """Creates new websocket connection if not open, requires capabilities and login into twitch IRC"""
        if not self._websocket.open:  # TODO: :meth:`_restart` must have way to reopen the websocket
            self._websocket = await websockets.connect(uri)
            # capabilities
            await self._send('CAP REQ :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
            # logging in
            if not self.is_anon:
                await self._send(f'PASS {self.token}')
                await self._send(f'NICK {self.login}')
            else:
                await self._send(f'NICK {self.login}')

    async def _read_websocket(
            self
    ) -> AsyncGenerator[IRCMessage, None]:
        """
        tries to read websocket:
            1. yields IRCMessage if successfully read;
            2. if `websockets.ConnectionClosedError`: reconnects irc if `self.should_restart`.
            3 if `websockets.ConnectionClosedOK`: `StopAsyncIteration`;
        also handles PING requests.
        """
        while True:
            try:
                raw_irc_messages = await self._websocket.recv()
            except ConnectionClosedOK:
                return
            # if websocket is closed
            except ConnectionClosedError:
                if self.is_restarting:
                    await self._running_restart_task
                elif self.should_restart:
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
            handler = self._COMMAND_HANDLERS[irc_msg.command]
        except KeyError:
            self._call_event('on_unknown_command', irc_msg)
        else:
            try:
                handler(self, irc_msg)
            except ChannelNotPrepared:
                await self._delay_irc_message(irc_msg)

    def _handle_names_part(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self._channels_accumulator.accumulate_part(irc_msg)

    def _handle_names_end(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if irc_msg.channel in self._channels_by_login:
            self._handle_names_update(irc_msg)
        else:
            self._channels_accumulator.accumulate_part(irc_msg)

    def _handle_names_update(
            self,
            irc_msg: IRCMessage
    ):
        channel = self._channels_by_login[irc_msg.channel]
        before = channel.names
        after = channel.names = self._channels_accumulator.pop_names(irc_msg.channel)  # if update no need to save parts
        self._call_event('on_names_update', channel, before, after)

    def _handle_roomstate(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if irc_msg.channel in self._channels_by_login:
            self._handle_channel_update(irc_msg)
        else:
            self._channels_accumulator.accumulate_part(irc_msg)

    def _handle_channel_update(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel = self._channels_by_login[irc_msg.channel]
        if hasattr(self, 'on_channel_update'):  # Channel.copy() cost us much time
            before = channel.copy()
            channel.update_state(irc_msg)
            after = channel.copy()
            self._call_event('on_channel_update', before, after)
        else:
            channel.update_state(irc_msg)

    def _handle_userstate(
            self,
            irc_msg: IRCMessage
    ) -> None:
        # prepare tags
        if 'user-login' not in irc_msg.tags:
            irc_msg.tags['user-login'] = self.login
        if 'user-id' not in irc_msg.tags:
            irc_msg.tags['user-id'] = self.global_state.id
        # if prepared
        if irc_msg.channel in self._channels_by_login:
            self._handle_userstate_update(irc_msg)
        else:
            self._channels_accumulator.accumulate_part(irc_msg)

    def _handle_userstate_update(
            self,
            irc_msg: IRCMessage
    ):
        channel = self._channels_by_login[irc_msg.channel]
        before = channel.client_state
        after = channel.client_state = LocalState(irc_msg)
        self._call_event('on_client_state_update', channel, before, after)

    def _handle_privmsg(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_message'):
            channel = self._get_prepared_channel(irc_msg.channel)
            if 'user-login' not in irc_msg.tags:
                irc_msg.tags['user-login'] = irc_msg.nickname
            author = ChannelUser(irc_msg, channel, self.send_whisper)
            message = ChannelMessage(irc_msg, channel, author)
            self._call_event('on_message', message)

    def _handle_whisper(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_whisper'):
            if 'user-login' not in irc_msg.tags:
                irc_msg.tags['user-login'] = irc_msg.nickname
            author = GlobalUser(irc_msg, self.send_whisper)
            whisper = Whisper(irc_msg, author)
            self._call_event('on_whisper', whisper)

    def _handle_join(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        self._call_event('on_user_join', channel, irc_msg.nickname)

    def _handle_part(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        self._call_event('on_user_part', channel, irc_msg.nickname)

    def _handle_notice(
            self,
            irc_msg: IRCMessage
    ) -> None:
        notice_id = irc_msg.tags.get('msg-id')
        if notice_id in ('msg_room_not_found', 'msg_channel_suspended'):
            self._handle_channel_join_error(irc_msg)
        elif notice_id.startswith('msg'):
            # NOTE: 'msg_room_not_found' & 'msg_channel_suspended' are handled in the previous condition
            self._handle_send_message_error(irc_msg)
        elif notice_id == 'cmds_available':
            self._handle_cmds_available(irc_msg)
        elif notice_id in ('room_mods', 'no_mods'):
            self._handle_mods(irc_msg)
        elif notice_id in ('vips_success', 'no_vips'):
            self._handle_vips(irc_msg)
        else:
            channel = self._get_prepared_channel(irc_msg.channel)
            self._call_event('on_notice', OnNotice(channel, notice_id, irc_msg.trailing))
            
    def _handle_channel_join_error(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.joined_channel_logins.discard(irc_msg.channel)
        reason = irc_msg.tags['msg-id'].removeprefix('msg_')
        self._call_event('on_channel_join_error', OnChannelJoinError(irc_msg.channel, reason, irc_msg.trailing))
            
    def _handle_send_message_error(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        reason = irc_msg.tags['msg-id'].removeprefix('msg_')
        self._call_event('on_send_message_error', OnSendMessageError(channel, reason, irc_msg.trailing))

    def _handle_cmds_available(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if (channel := self.get_channel(irc_msg.channel)) is None:
            self._channels_accumulator.accumulate_part(irc_msg)
        else:
            raw_commands = irc_msg.trailing.removesuffix(' More help: https://help.twitch.tv/s/article/chat-commands')
            raw_commands = raw_commands.split(': ', 1)[1]  # 'Commands available to you in this room (...): '
            before = channel.commands
            after = channel.commands = tuple(raw_commands.split(' '))
            self._call_event('on_commands_update', channel, before, after)

    def _handle_mods(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if (channel := self.get_channel(irc_msg.channel)) is None:
            self._channels_accumulator.accumulate_part(irc_msg)
        else:
            raw_mods = irc_msg.trailing.split(': ', 1)[1]
            before = channel.mods
            after = channel.mods = tuple(raw_mods.split(', '))
            self._call_event('on_mods_update', channel, before, after)

    def _handle_vips(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if (channel := self.get_channel(irc_msg.channel)) is None:
            self._channels_accumulator.accumulate_part(irc_msg)
        else:
            raw_vips = irc_msg.trailing.split(': ', 1)[1]
            raw_vips = raw_vips.removesuffix('.')
            before = channel.vips
            after = channel.vips = tuple(raw_vips.split(', '))
            self._call_event('on_vips_update', channel, before, after)

    def _handle_clearchat(
            self,
            irc_msg: IRCMessage
    ) -> None:
        # if clear user
        if irc_msg.trailing:  # text contains login of the user
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
            channel = self._get_prepared_channel(irc_msg.channel)
            # values
            target_user_login = irc_msg.trailing
            target_user_id = irc_msg.tags.get('target-user-id')
            target_message_id = irc_msg.tags.get('target-msg-id')
            ban_duration = int(irc_msg.tags.get('ban-duration', 0))
            # handle later
            self._call_event(
                'on_clear_chat_from_user',
                channel,  OnClearChatFromUser(target_user_login, target_user_id, target_message_id, ban_duration)
            )

    def _handle_clear_chat(
            self,
            irc_msg: IRCMessage
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        self._call_event('on_clear_chat', channel)

    def _handle_clearmsg(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_message_delete'):
            # channel
            channel = self._get_prepared_channel(irc_msg.channel)
            # values
            user_login = irc_msg.tags.get('login')
            message_id = irc_msg.tags.get('target-msg-id')
            tmi_time = int(irc_msg.tags.get('tmi-sent-ts', 0))
            # handle later
            self._call_event(
                'on_message_delete',
                OnMessageDelete(channel, user_login, irc_msg.trailing, message_id, tmi_time)
            )

    def _handle_usernotice(
            self,
            irc_msg: IRCMessage
    ) -> None:
        # channel
        channel = self._get_prepared_channel(irc_msg.channel)
        # select handler
        try:
            event_type = irc_msg.tags.get('msg-id')
            event_name, event_class = self._USER_EVENT_TYPES[event_type]
        # if unknown event
        except KeyError:
            self._call_event('on_unknown_user_event', irc_msg)
        # if known event
        else:
            # if has specified handler
            if hasattr(self, event_name):
                author = ChannelUser(irc_msg, channel, self.send_whisper)
                event = event_class(irc_msg, author, channel)
                self._call_event(event_name, event)
            # if has not specified handler
            elif hasattr(self, 'on_user_event'):
                author = ChannelUser(irc_msg, channel, self.send_whisper)
                event = event_class(irc_msg, author, channel)
                self._call_event('on_user_event', event)

    def _handle_hosttarget(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_host_start') or hasattr(self, 'on_host_stop'):
            host_login, viewers_count = irc_msg.trailing.split(' ', 1)
            if host_login == '-':
                self._handle_host_start(irc_msg)
            else:
                self._handle_host_stop(irc_msg)

    def _handle_host_start(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_host_start'):
            host_login, viewers_count = irc_msg.trailing.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else 0
            self._call_event('on_host_start', host_login, viewers_count)

    def _handle_host_stop(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if hasattr(self, 'on_host_stop'):
            _, viewers_count = irc_msg.trailing.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else None
            self._call_event('on_host_stop', viewers_count)

    def _handle_globaluserstate(
            self,
            irc_msg: IRCMessage
    ):
        if 'user-login' not in irc_msg.tags:
            irc_msg.tags['user-login'] = self.login
        if hasattr(self, 'on_global_state_update'):
            before = self.global_state
            self.global_state = GlobalState(irc_msg)
            after = self.global_state
            self._call_event('on_global_state_update', before, after)
        else:
            self.global_state = GlobalState(irc_msg)

    def _handle_reconnect(
            self,
            _: IRCMessage
    ):
        self._do_later(self.restart())  # does not close connection if open

    def _handle_ping(
            self,
            _: IRCMessage
    ):
        self._do_later(self._send('PONG :tmi.twitch.tv'))

    def _save_channel(
            self,
            channel: Channel
    ) -> None:
        """
        1. Adds it in `self._channels_by_id` and `self._channels_by_login`
        3. Creates async tasks that will handle every delayed message
        2. Calls event handler `self.on_channel_join`

        Args:
            channel: `Channel`
                will be saved

        Returns:
            `None`
        """
        self._channels_by_id[channel.id] = channel
        self._channels_by_login[channel.login] = channel
        # handle delayed irc_messages
        delayed_irc_messages = self._delayed_irc_msgs.pop(channel.login, ())
        for delayed_irc_message in delayed_irc_messages:
            self._do_later(
                self._handle_command(delayed_irc_message)
            )
        self._call_event('on_channel_join', channel)

    async def _send(
            self,
            irc_message: str
    ) -> None:
        """
        Sends irc message to twitch irc server

        Args:
            irc_message: `str`
                command to send

        Returns:
            `None`
        """
        while True:
            try:
                await self._websocket.send(irc_message + '\r\n')
            except ConnectionClosedError:  # if :meth:`stop` is called there is :exc:`ConnectionClosedOK`
                if self.is_restarting:
                    await self._running_restart_task  # if :meth:`restart` is running don't call it once more
                elif self.should_restart:
                    await self.restart()
                else:
                    raise
            except ConnectionClosedOK as e:
                raise ConnectionClosedOK('Connection was closed by :meth:`stop()`') from e
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
                login of a channel via the whisper must be sent

        Returns:
            `None`
        """
        if agent is None:
            agent = self.whisper_agent
        # send
        content = f'/w {target} {content}'
        await self.send_message(agent, content)

    async def join_channel(
            self,
            login: str
    ) -> None:
        """Sends command to join the channel and adds its login to `self.joined_channels_logins`"""
        self.joined_channel_logins.add(login)
        await self._send(f'JOIN #{login}')
        await self._request_channel_parts(login)

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
        if logins:  # don't join to no channel
            self.joined_channel_logins.update(logins)
            logins_str = ',#'.join(logins)
            await self._send(f'JOIN #{logins_str}')
        for login in logins:
            await self._request_channel_parts(login)

    async def _request_channel_parts(self, login: str):
        """ Requests commands list, mods list, vips list for the :class:`Channel` with given `login` """
        if self.should_accum_commands:
            await self.send_message(login, '/help')
        if self.should_accum_mods:
            await self.send_message(login, '/mods')
        if self.should_accum_vips:
            await self.send_message(login, '/vips')

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

    async def _delay_irc_message(self, irc_msg: IRCMessage) -> None:
        """
        Delays `irc_msg`.
        Delayed message will be handled after the channel with `channel_login` is created

        Args:
            irc_msg: `IRCMessage`
                message to be delayed

        Returns:
            `None`
        """
        delayed_irc_messages = self._delayed_irc_msgs.setdefault(irc_msg.channel, [])
        if len(delayed_irc_messages) == 10:
            # something's wrong if there are 10 delayed messages, better try to reconnect
            await self.join_channel(irc_msg.channel)
            print(f'Try to rejoin #{irc_msg.channel}')  # TODO: modify the print into logging
            delayed_irc_messages.append(irc_msg)
        # protection from memory overflow
        elif len(delayed_irc_messages) == 30:
            print(f'#{irc_msg.channel} has delayed msgs overflow')  # TODO: modify the print into logging
            delayed_irc_messages.append(irc_msg)
        elif len(delayed_irc_messages) > 30:
            pass
        else:
            delayed_irc_messages.append(irc_msg)

    def _call_event(
            self,
            event_name: str,
            *args
    ):
        if (event := getattr(self, event_name, None)) is not None:
            self._do_later(
                event(*args)
            )

    def event(self, coro: Callable[..., Coroutine]) -> Callable[[], Coroutine]:
        """
        |DECORATOR|
        registers handler of event

        Args:
            coro: Coroutine
                a Coroutine that will be called when the event would be happened, should has known name of event

        Raises:
            errors.UnknownEvent
                if got unknown event's name
            errors.FunctionIsNotCoroutine
                if `coro` is not Coroutine

        Returns:
            Coroutine:
                the object that the method got in `coro` as argument
        """
        self._register_event(coro.__name__, coro)
        return coro

    def _register_event(
            self,
            handler_name: str,
            coro: Callable[..., Coroutine]
    ) -> None:
        """
        1. Registers event with given name.
        2. Checks that the `coro` is Coroutine.
        3. Checks that the `handler_name` is known.

        Args:
            handler_name: `str`
                name of handler, should be known
            coro: Coroutine
                coroutine that must handle specified event.

        Returns:
            `None`
        """
        if not iscoroutinefunction(coro):
            raise TypeError(f'given object `{coro.__name__}` is not a coroutine function')
        # if event
        if handler_name in self.EVENTS:
            setattr(self, handler_name, coro)
        # if user event
        elif handler_name in self.USER_EVENTS:
            setattr(self, handler_name, coro)
        else:  # what for a developer will register unknown event? better tell that person about
            raise NameError(f'"{handler_name}" is unknown name of event')

    def _do_later(
            self,
            coro: Awaitable
    ) -> None:
        """Creates async task in `self.loop`"""
        self.loop.create_task(coro)

    _COMMAND_HANDLERS: Dict[str, Callable[[_Client, IRCMessage], Any]] = {
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
        '353': _handle_names_part,
        '366': _handle_names_end
    }

    _USER_EVENT_TYPES: Dict[str, Tuple[str, Any]] = {
        # event_type(or 'msg-id'): (event_handler, event_class)
        'sub': ('on_sub', Sub),
        'resub': ('on_resub', ReSub),
        'subgift': ('on_sub_gift', SubGift),
        'submysterygift': ('on_sub_mystery_gift', SubMysteryGift),
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
        'on_channel_join', 'on_channel_update',  # ROOMSTATE
        'on_client_state_update',  # USERSTATE
        'on_names_update',  # 366
        'on_ready', 'on_global_state_update',  # GLOBALUSERSTATE
        'on_user_join',  # JOIN
        'on_user_part',  # PART
        'on_clear_chat_from_user', 'on_clear_chat',  # CLEARCHAT
        'on_message_delete',  # CLEARMSG
        'on_host_start', 'on_host_stop',  # HOSTTARGET
        'on_notice', 'on_channel_join_error', 'on_send_message_error',  # NOTICE
        'on_commands_update', 'on_mods_update', 'on_vips_update',  # NOTICE
        'on_user_event', 'on_unknown_user_event',  # USERNOTICE
        'on_reconnect', 'on_unknown_command',
    )

    USER_EVENTS = (
        'on_sub', 'on_resub', 'on_sub_gift', 'on_sub_mystery_gift',  # subs
        'on_prime_paid_upgrade', 'on_gift_paid_upgrade',  # upgrades
        'on_standard_pay_forward', 'on_community_pay_forward',  # payments forward
        'on_bits_badge_tier',  # bits badges tier
        'on_reward_gift',  # rewards
        'on_raid', 'on_unraid',  # raids
        'on_ritual', # rituals
    )
