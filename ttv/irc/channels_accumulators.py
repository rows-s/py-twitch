from typing import Callable, Coroutine, Dict, Union, List, Tuple, TypeVar
from .channel import Channel
from .irc_message import IRCMessage
from .user_states import LocalState


__all__ = ('ChannelsAccumulator',)

_ChannelsAccumulator = TypeVar('_ChannelsAccumulator')


class ChannelsAccumulator:  # TODO: delete all the accum args and add channel_accumulation_cooldown
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
            should_accum_client_states=True,
            should_accum_names=False,
            should_accum_commands=False,
            should_accum_mods=False,
            should_accum_vips=False,
    ) -> None:
        # callbacks
        self.channel_ready_callback: Callable[[Channel], None] = channel_ready_callback
        self.send_callback: Callable[[str], Coroutine] = send_callback
        self.channel_states: Dict[str, IRCMessage] = {}

        self.should_accum_client_states: bool = should_accum_client_states
        self.client_states: Dict[str, LocalState] = {}

        self.should_accum_names: bool = should_accum_names
        self.names: Dict[str, Union[List[str], Tuple[str]]] = {}

        self.should_accum_commands: bool = should_accum_commands
        self.commands: Dict[str, Tuple[str, ...]] = {}

        self.should_accum_mods: bool = should_accum_mods
        self.mods: Dict[str, Tuple[str, ...]] = {}

        self.should_accum_vips: bool = should_accum_vips
        self.vips: Dict[str, Tuple[str, ...]] = {}

    def accumulate_part(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if irc_msg.command != 'NOTICE':
            try:
                handler = self.HANDLERS[irc_msg.command]
            except KeyError:
                return
        else:
            try:
                handler = self.NOTICE_HANDLERS[irc_msg.tags['msg-id']]
            except KeyError:
                return
        handler(self, irc_msg)
        if self.is_channel_ready(irc_msg.channel):
            self.call_channel_ready_callback(irc_msg.channel)

    def update_room_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        if (room_state := self.channel_states.get(irc_msg.channel)) is None:
            self.channel_states[irc_msg.channel] = irc_msg
        else:
            room_state.tags.update(irc_msg.tags)  # if an update during accumulation (tags might be not completed)

    def update_client_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.client_states[irc_msg.channel] = LocalState(irc_msg)

    def update_names(
            self,
            irc_msg: IRCMessage
    ) -> None:
        new_names = irc_msg.trailing.split(' ')
        if (names := self.names.get(irc_msg.channel)) is None:
            self.names[irc_msg.channel] = new_names
        else:
            self.names[irc_msg.channel] = list(names) + new_names

    def end_names(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.names[irc_msg.channel] = tuple(self.names[irc_msg.channel])

    def pop_names(
            self,
            channel_login: str
    ) -> Tuple[str]:
        return tuple(self.names.pop(channel_login))

    def update_commands(
            self,
            irc_msg: IRCMessage
    ):
        raw_cmds = irc_msg.trailing.split(' More')[0]
        raw_cmds = raw_cmds.split(': ', 1)[1]  # 'Commands available to you in this room (...): '
        self.commands[irc_msg.channel] = tuple(raw_cmds.split(' '))

    def update_mods(
            self,
            irc_msg: IRCMessage
    ):
        if irc_msg.tags['msg-id'] == 'no_mods':
            self.mods[irc_msg.channel] = ()
        else:
            raw_mods = irc_msg.trailing.split(': ', 1)[1]
            mods = raw_mods.split(', ')
            self.mods[irc_msg.channel] = tuple(mods)

    def update_vips(
            self,
            irc_msg: IRCMessage
    ):
        if irc_msg.tags['msg-id'] == 'no_vips':
            self.vips[irc_msg.channel] = ()
        else:
            raw_vips = irc_msg.trailing.split(': ', 1)[1].removesuffix('.')
            vips = raw_vips.split(', ')
            self.vips[irc_msg.channel] = tuple(vips)

    def is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        try:
            assert isinstance(self.channel_states.get(channel_login), IRCMessage)
            if self.should_accum_client_states:
                assert channel_login in self.client_states
            if self.should_accum_names:
                assert isinstance(self.names.get(channel_login), tuple)
            if self.should_accum_commands:
                assert channel_login in self.commands
            if self.should_accum_mods:
                assert channel_login in self.mods
            if self.should_accum_vips:
                assert channel_login in self.vips
        except AssertionError:
            return False
        else:
            return True

    def call_channel_ready_callback(self, channel_login: str):
        self.channel_ready_callback(
            self.create_channel(channel_login)
        )

    def create_channel(
            self,
            channel_login: str
    ) -> Channel:
        room_state = self.channel_states.pop(channel_login)
        client_state = self.client_states.pop(channel_login, self.EMPTY_CLIENT_STATE)
        names = self.names.pop(channel_login, ())
        commands = self.commands.pop(channel_login, ())
        mods = self.mods.pop(channel_login, ())
        vips = self.vips.pop(channel_login, ())
        return Channel(room_state, client_state, names, commands, mods, vips, self.send_callback)

    EMPTY_CLIENT_STATE = LocalState(IRCMessage.create_empty())

    HANDLERS: Dict[str, Callable[[_ChannelsAccumulator, IRCMessage], None]] = {
        'ROOMSTATE': update_room_state,
        'USERSTATE': update_client_state,
        '353': update_names,
        '366': end_names,
    }

    NOTICE_HANDLERS: Dict[str, Callable[[_ChannelsAccumulator, IRCMessage], None]] = {
        'cmds_available': update_commands,
        'room_mods': update_mods,
        'no_mods': update_mods,
        'vips_success': update_vips,
        'no_vips': update_vips,
    }
