import asyncio
from asyncio import Task
from typing import Callable, Dict, Union, List, Tuple, Optional

from .channel import Channel
from .irc_connections import TTVIRCClient
from .irc_messages import TwitchIRCMsg
from .user_states import LocalState

__all__ = ('ChannelsAccumulator', 'ChannelParts')


class ChannelParts:
    """
    Class represents all the parts of :class:`Channel` as raw_state, client_state, names, commands, mods, vips

    :meth:`add_part` takes irc_msg with a raw part and parse the part from it
    """
    def __init__(
            self,
            login: str
    ):
        self.login: str = login
        self.raw_channel_state: Optional[TwitchIRCMsg] = None
        self.client_state: Optional[LocalState] = None
        self.names: Optional[Union[List, Tuple]] = None
        self.commands: Optional[Tuple[str]] = None
        self.mods: Optional[Tuple[str]] = None
        self.vips: Optional[Tuple[str]] = None

    @property
    def is_ready(self) -> str:
        """
        marks if the parts are ready, anonymously ready or not ready. Marks with the class' attrs:
            self.NOT_READY:
                represents that the parts are not ready at all
            self.READY_ANON:
                represents that the parts are ready as during anonymous logging in (have `raw_client_state` and `names`)
            self.READY:
                represents that the parts are ready (have all the parts)

        Examples:
            >>> parts = ChannelParts('target')
            >>> if parts.is_ready == parts.READY:
            >>>     print('Wow!')
        """
        try:
            ready_type: str = self.NOT_READY
            assert self.raw_channel_state is not None
            assert isinstance(self.names, tuple)  # migth be a list (unended names)
            ready_type = self.READY_ANON
            assert self.client_state is not None
            assert self.commands is not None
            assert self.mods is not None
            assert self.vips is not None
            ready_type = self.READY
        except AssertionError:
            pass
        return ready_type

    def add_part(
            self,
            irc_msg: TwitchIRCMsg
    ):
        """
        Takes raw part as a instance of :class:`TwitchIRCMsg` and parse the part to the respective attribute

        Args:
            irc_msg: :class:`TwitchIRCMsg`
                raw part to be parsed

        Notes:
            if you want to add a parsed part you can just set the attr
        """
        try:
            handler = self._get_handler_for_irc_msg(irc_msg)
        except KeyError:
            return
        else:
            handler(self, irc_msg)

    def create_channel(
            self,
            irc_conn: TTVIRCClient
    ) -> Channel:
        """
        Args:
            irc_conn:
                will be passed as the :class:`Channel`'s argument

        Returns:
            created Channel
        """
        return Channel(
            self._get_raw_channel_state(),
            self.client_state or LocalState(TwitchIRCMsg.create_empty()),
            self.names or (),
            self.commands or (),
            self.mods or (),
            self.vips or (),
            irc_conn,
        )

    def _get_raw_channel_state(self) -> TwitchIRCMsg:
        if self.raw_channel_state:
            return self.raw_channel_state
        else:
            raw_channel_state = TwitchIRCMsg.create_empty()
            raw_channel_state.channel = self.login
            return raw_channel_state

    def _get_handler_for_irc_msg(
            self,
            irc_msg: TwitchIRCMsg
    ) -> Callable[['ChannelParts', TwitchIRCMsg], None]:
        if irc_msg.command != 'NOTICE':
            return self._HANDLERS[irc_msg.command]
        else:
            return self._NOTICE_HANDLERS[irc_msg.msg_id]

    def _update_channel_state(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if self.raw_channel_state is None:
            self.raw_channel_state = irc_msg
        else:
            self.raw_channel_state.update(irc_msg)

    def _update_client_state(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        self.client_state = LocalState(irc_msg)

    def _update_names(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        names = irc_msg.trailing.split(' ')
        if isinstance(self.names, list):
            self.names += names
        else:
            self.names = names

    def _end_names(
            self,
            _: TwitchIRCMsg
    ) -> None:
        self.names = tuple(self.names)

    def _update_commands(
            self,
            irc_msg: TwitchIRCMsg
    ):
        raw_cmds = irc_msg.trailing.split(' More')[0]
        raw_cmds = raw_cmds.split(': ', 1)[1]  # 'Commands available to you in this room (...): '
        self.commands = tuple(raw_cmds.split(' '))

    def _update_mods(
            self,
            irc_msg: TwitchIRCMsg
    ):
        if irc_msg.msg_id == 'no_mods':
            mods = ()
        else:
            raw_mods = irc_msg.trailing.split(': ', 1)[1]
            mods = raw_mods.split(', ')
        self.mods = tuple(mods)

    def _update_vips(
            self,
            irc_msg: TwitchIRCMsg
    ):
        if irc_msg.msg_id == 'no_vips':
            vips = ()
        else:
            raw_vips = irc_msg.trailing.split(': ', 1)[1].removesuffix('.')
            vips = raw_vips.split(', ')
        self.vips = tuple(vips)

    NOT_READY = 'NOT_READY'
    READY_ANON = 'READY_ANON'
    READY = 'READY'

    _EMPTY_CLIENT_STATE = LocalState(TwitchIRCMsg.create_empty())

    _HANDLERS: Dict[str, Callable[['ChannelParts', TwitchIRCMsg], None]] = {
        'ROOMSTATE': _update_channel_state,
        'USERSTATE': _update_client_state,
        '353': _update_names,
        '366': _end_names,
    }

    _NOTICE_HANDLERS: Dict[str, Callable[['ChannelParts', TwitchIRCMsg], None]] = {
        'cmds_available': _update_commands,
        'room_mods': _update_mods,
        'no_mods': _update_mods,
        'vips_success': _update_vips,
        'no_vips': _update_vips,
    }


class ChannelsAccumulator:
    """
    Class gives interfaces of channels' parts accumulation.

    Callback usage:
        1. Calls given :arg:`channel_ready_callback()` when a parts are ready according the anon-type (:arg:`is_anon`)
        2. Calls when the timeout is expired. Timeout is canceled if the channel is ready
        3. Timeouts are being handled only after calling :meth:`start_accumulation()`
        4. To don't use timeout feature don't call :meth:`start_accumulation()`
        5. There is :meth:`abort_accumulation()` that removes the timeout task and accumulated parts.

    Args:
        channel_ready_callback:
            A function that gets 1 positional argument :class:`Channel`
        irc_conn:
            IRCClient uses to send messages
        accumulation_timeout:
            The value of time limit for channel's accumulation. Default: 5.
        is_anon:
            The flag affects when a channel is considered as ready. Default: False.
     """
    def __init__(
            self,
            *,
            channel_ready_callback: Callable[[Channel], None],
            irc_conn: TTVIRCClient,
            accumulation_timeout: float = 50,
            is_anon: bool = False
    ) -> None:
        self._channel_ready_callback: Callable[[Channel], None] = channel_ready_callback
        self._irc_conn: TTVIRCClient = irc_conn
        self._all_parts: Dict[str, ChannelParts] = {}
        self._timeout: float = accumulation_timeout
        self._timeout_tasks: Dict[str, Task] = {}
        self.is_anon: bool = is_anon

    async def start_accumulations(
            self,
            *channels: str
    ):
        """
        Adds timeout task for the given channel login. Creates :class:'ChannelParts' in advance.

        Args:
            channels:
                login of the channel to be accumulated
        """
        await self.abort_accumulations(*channels, msg='Restarting accumulation')
        for channel in channels:
            await self._add_timeout(channel)
            self._all_parts[channel] = ChannelParts(channel)
            await self._request_channel_parts(channel)

    async def abort_accumulations(
            self,
            *channels: str,
            msg: str = None
    ) -> None:
        """
        Cancels the timeout task if exists.

        Args:
            channels:
                login of the channel whose accumulation must be aborted
            msg:
                msg for the canceled task
        """
        msg = msg or 'Accumulation abort'
        for channel in channels:
            await self._remove_timeout(channel, msg=msg)
            self._all_parts.pop(channel, None)

    async def accumulate_part(
            self,
            irc_msg: TwitchIRCMsg
    ):
        """
        Add new given part to the respective :class:`ChannelParts`. Creates new :class:`ChannelParts` if not exists.
        Checks if the :class:`ChannelParts` are ready and call the `self.channel_ready_callback` if so.

        Args:
            irc_msg:
                raw part
        """
        parts = await self._setdefault_parts(irc_msg.channel)
        parts.add_part(irc_msg)
        if await self.is_channel_ready(irc_msg.channel):
            await self._call_channel_ready_callback(irc_msg.channel)

    async def get_parts(self, channel_login: str) -> ChannelParts:
        return self._all_parts.get(channel_login) or ChannelParts(channel_login)

    async def _request_channel_parts(self, login: str):
        """ Requests commands list, mods list, vips list for the channel with given `login` """
        if not self.is_anon:
            await self._irc_conn.send_msg(login, '/help')
            await self._irc_conn.send_msg(login, '/mods')
            await self._irc_conn.send_msg(login, '/vips')

    async def is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        """
       Marks if the :class:`ChannelParts` are ready according the anonymous type (self.is_anon or not)

        Args:
            channel_login:
                login of the channel whose parts must be checked

        Returns: :class:`bool`
        """
        if (parts := self._all_parts.get(channel_login)) is None:
            return False
        elif not self.is_anon:
            return parts.is_ready == parts.READY
        else:
            return parts.is_ready in (parts.READY_ANON, parts.READY)

    async def _setdefault_parts(self, channel_login: str) -> ChannelParts:
        try:
            return self._all_parts[channel_login]
        except KeyError:
            self._all_parts[channel_login] = (parts := ChannelParts(channel_login))
            return parts

    async def _add_timeout(
            self,
            channel_login: str
    ):
        self._timeout_tasks[channel_login] = asyncio.create_task(self._channel_ready_timeout(channel_login))

    async def _remove_timeout(
            self,
            channel_login: str,
            msg: Optional[str] = None
    ):
        if (timeout_task := self._timeout_tasks.pop(channel_login, None)) is not None:
            timeout_task.cancel(msg)

    async def _channel_ready_timeout(self, channel_login: str):
        await asyncio.sleep(self._timeout)
        await self._call_channel_ready_callback(channel_login, by_timeout=True)

    async def _call_channel_ready_callback(
            self,
            channel_login: str,
            *,
            by_timeout: bool = False
    ):
        msg = 'Channel ready' + (' timeout' if by_timeout else '')
        parts = await self.get_parts(channel_login)
        await self.abort_accumulations(channel_login, msg=msg)
        self._channel_ready_callback(parts.create_channel(irc_conn=self._irc_conn))
