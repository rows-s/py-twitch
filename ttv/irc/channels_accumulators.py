import asyncio
from asyncio import Task
from typing import Callable, Coroutine, Dict, Union, List, Tuple, TypeVar, Optional
from .channel import Channel
from .irc_message import IRCMessage
from .user_states import LocalState


__all__ = ('ChannelsAccumulator',)

_ChannelsAccumulator = TypeVar('_ChannelsAccumulator')


class ChannelsAccumulator:  # TODO: delete all the accum args and add channel_accumulation_cooldown
    # TODO: add channel_accumulation_timeout
    """
    Object of the class gives interfaces of accumulation of channels' parts.
    Accumulates ROOMSTATE, USERSTATE, names(353, 366).
    Calls :func:`channel_ready_callback` callback passing :class:`Channel` when a channel is ready.
    """
    def __init__(
            self,
            channel_ready_callback: Callable[[Channel], None],
            send_callback: Callable[[str], Coroutine],
            *,
            accumulation_timeout: float = 5,
            is_anon: bool = False
    ) -> None:
        # callbacks
        self.channel_ready_callback: Callable[[Channel], None] = channel_ready_callback
        self.send_callback: Callable[[str], Coroutine] = send_callback
        self.channel_states: Dict[str, IRCMessage] = {}
        self.client_states: Dict[str, LocalState] = {}
        self.names: Dict[str, Union[List[str], Tuple[str]]] = {}
        self.commands: Dict[str, Tuple[str, ...]] = {}
        self.mods: Dict[str, Tuple[str, ...]] = {}
        self.vips: Dict[str, Tuple[str, ...]] = {}
        self.timeout_tasks: Dict[str, Task] = {}

        self._timeout: float = accumulation_timeout
        self.is_anon: bool = is_anon

    def accumulate_part(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if irc_msg.channel is None:
            return

        try:
            handler = self._get_handler_for_irc_msg(irc_msg)
        except KeyError:
            return
        else:
            handler(self, irc_msg)

        if self._is_channel_ready(irc_msg.channel):
            self._call_channel_ready_callback(irc_msg.channel)
        else:
            self.add_timeout(irc_msg.channel)  # sets timeout if not ready and if timeout hasn't been set

    def _get_handler_for_irc_msg(
            self,
            irc_msg: IRCMessage
    ):
        if irc_msg.command != 'NOTICE':
            return self._HANDLERS[irc_msg.command]
        else:
            return self._NOTICE_HANDLERS[irc_msg.tags['msg-id']]

    def add_timeout(
            self,
            channel_login: str,
            should_replace: bool = False
    ):
        if should_replace:
            self.remove_timeout(channel_login)
        self.timeout_tasks[channel_login] = asyncio.create_task(
            self._call_channel_ready_callback_after_timeout(channel_login)
        )

    def remove_timeout(
            self,
            channel_login: str,
            msg: Optional[str] = None
    ):
        if (timeout_task := self.timeout_tasks.pop(channel_login, None)) is not None:
            timeout_task.cancel(msg)

    async def _call_channel_ready_callback_after_timeout(self, channel_login: str):
        await asyncio.sleep(self._timeout)
        self._call_channel_ready_callback(channel_login)

    def _update_room_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if (room_state := self.channel_states.get(irc_msg.channel)) is None:
            self.channel_states[irc_msg.channel] = irc_msg
        else:
            room_state.tags.update(irc_msg.tags)  # if an update during accumulation (tags might be not completed)

    def _update_client_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.client_states[irc_msg.channel] = LocalState(irc_msg)

    def _update_names(
            self,
            irc_msg: IRCMessage
    ) -> None:
        new_names = irc_msg.trailing.split(' ')
        if (names := self.names.get(irc_msg.channel)) is None:
            self.names[irc_msg.channel] = new_names
        else:
            self.names[irc_msg.channel] = list(names) + new_names

    def _end_names(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.names[irc_msg.channel] = tuple(self.names[irc_msg.channel])

    def pop_names(
            self,
            channel_login: str
    ) -> Tuple[str]:
        return tuple(self.names.pop(channel_login))

    def _update_commands(
            self,
            irc_msg: IRCMessage
    ):
        raw_cmds = irc_msg.trailing.split(' More')[0]
        raw_cmds = raw_cmds.split(': ', 1)[1]  # 'Commands available to you in this room (...): '
        self.commands[irc_msg.channel] = tuple(raw_cmds.split(' '))

    def _update_mods(
            self,
            irc_msg: IRCMessage
    ):
        if irc_msg.tags['msg-id'] == 'no_mods':
            self.mods[irc_msg.channel] = ()
        else:
            raw_mods = irc_msg.trailing.split(': ', 1)[1]
            mods = raw_mods.split(', ')
            self.mods[irc_msg.channel] = tuple(mods)

    def _update_vips(
            self,
            irc_msg: IRCMessage
    ):
        if irc_msg.tags['msg-id'] == 'no_vips':
            self.vips[irc_msg.channel] = ()
        else:
            raw_vips = irc_msg.trailing.split(': ', 1)[1].removesuffix('.')
            vips = raw_vips.split(', ')
            self.vips[irc_msg.channel] = tuple(vips)

    def _is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        try:
            assert isinstance(self.channel_states.get(channel_login), IRCMessage)
            assert isinstance(self.names.get(channel_login), tuple)
            if self.is_anon:
                assert channel_login in self.client_states
                assert channel_login in self.commands
                assert channel_login in self.mods
                assert channel_login in self.vips
        except AssertionError:
            return False
        else:
            return True

    def _call_channel_ready_callback(
            self,
            channel_login: str
    ):
        self.channel_ready_callback(
            self._create_channel(channel_login)
        )

    def _create_channel(
            self,
            channel_login: str
    ) -> Channel:
        self.remove_timeout(channel_login)
        if (room_state := self.channel_states.pop(channel_login)) is None:
            room_state = IRCMessage.create_empty()
        client_state = self.client_states.pop(channel_login, self._EMPTY_CLIENT_STATE)
        names = self.names.pop(channel_login, ())
        commands = self.commands.pop(channel_login, ())
        mods = self.mods.pop(channel_login, ())
        vips = self.vips.pop(channel_login, ())
        return Channel(room_state, client_state, names, commands, mods, vips, self.send_callback)

    _EMPTY_CLIENT_STATE = LocalState(IRCMessage.create_empty())

    _HANDLERS: Dict[str, Callable[[_ChannelsAccumulator, IRCMessage], None]] = {
        'ROOMSTATE': _update_room_state,
        'USERSTATE': _update_client_state,
        '353': _update_names,
        '366': _end_names,
    }

    _NOTICE_HANDLERS: Dict[str, Callable[[_ChannelsAccumulator, IRCMessage], None]] = {
        'cmds_available': _update_commands,
        'room_mods': _update_mods,
        'no_mods': _update_mods,
        'vips_success': _update_vips,
        'no_vips': _update_vips,
    }
