from .irc_message import IRCMessage
from .user_states import LocalState

from typing import Callable, Dict, Union, List, Tuple, Coroutine

__all__ = ('Channel', 'ChannelsAccumulator', 'AnonChannelsAccumulator')


class Channel:
    def __init__(
            self,
            irc_msg: IRCMessage,
            client_state: LocalState,
            names: Tuple[str, ...],
            commands: Tuple[str, ...],
            _send_callback: Callable[[str], Coroutine]
    ) -> None:
        self._irc_msg: IRCMessage = irc_msg
        self.client_state: LocalState = client_state
        # TODO: logically the class must not have this variable (client_state),
        #  because it represents state of a :class:`Client` not anything of :class:`Channel`.
        #  But that way's easier to understand and to use
        self.names: Tuple[str, ...] = names
        self.commands: Tuple[str, ...] = commands
        self._send: Callable[[str], Coroutine] = _send_callback

    @property
    def id(self) -> str:
        return self._irc_msg.tags.get('room-id')

    @property
    def login(self) -> str:
        return self._irc_msg.channel

    @property
    def is_unique_only(self) -> bool:
        return self._irc_msg.tags.get('r9k') == '1'

    @property
    def is_emote_only(self) -> bool:
        return self._irc_msg.tags.get('emote-only') == '1'

    @property
    def is_subs_only(self) -> bool:
        return self._irc_msg.tags.get('subs-only') == '1'

    @property
    def has_rituals(self) -> bool:
        return self._irc_msg.tags.get('rituals') == '1'

    @property
    def slow_seconds(self) -> int:
        return int(self._irc_msg.tags.get('slow', 0))

    @property
    def is_slow(self) -> bool:
        return self.slow_seconds != 0

    @property
    def followers_only_minutes(self) -> int:
        return int(self._irc_msg.tags.get('followers-only', 0))

    @property
    def is_followers_only(self) -> bool:
        return self.followers_only_minutes != -1

    def update_state(
            self,
            irc_msg: IRCMessage
    ):
        """
        Updates state-attributes with new values provided in :arg:`irc_msg`.

        Notes:
            Does not change a value if there isn't the value in `irc_msg`.
        Args:
            irc_msg :class:`IRCMessage`:
                 IRCMessage with new values
        """
        self._irc_msg.tags.update(irc_msg.tags)

    def copy(self):
        return self.__class__(self._irc_msg.copy(), self.client_state.copy(), self.names, self.commands, self._send)

    async def send_message(
            self,
            content: str
    ) -> None:
        await self._send(f'PRIVMSG #{self.login} :{content}')

    async def request_state_update(self):
        await self._send(f'JOIN #{self.login}')

    async def request_commands(self):
        await self.send_message('/help')

    async def clear(self):
        await self.send_message('/clear')

    def __eq__(self, other):
        if isinstance(other, Channel):
            return self._irc_msg == other._irc_msg
        return False


class ChannelsAccumulator:
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
            should_accum_commands=False
    ) -> None:
        self.channel_states: Dict[str, IRCMessage] = {}
        self.client_states: Dict[str, LocalState] = {}
        self.names: Dict[str, Union[List[str], Tuple[str]]] = {}
        self.commands: Dict[str, Tuple[str, ...]] = {}
        self.channel_ready_callback: Callable[[Channel], None] = channel_ready_callback
        self.send_callback: Callable[[str], Coroutine] = send_callback
        self.should_accum_commands: bool = should_accum_commands

    def update_room_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        room_state = self.channel_states.get(irc_msg.channel)
        if room_state is None:
            self.channel_states[irc_msg.channel] = irc_msg
        else:
            room_state.tags.update(irc_msg.tags)
        if self.is_channel_ready(irc_msg.channel):
            self.call_channel_ready_callback(irc_msg.channel)

    def update_client_state(
            self,
            irc_msg: IRCMessage
    ) -> None:  # TODO: must be condition for cases when client_state already exists
        self.client_states[irc_msg.channel] = LocalState(irc_msg)
        if self.is_channel_ready(irc_msg.channel):
            self.call_channel_ready_callback(irc_msg.channel)

    def update_names(
            self,
            irc_msg: IRCMessage
    ) -> None:
        new_names = irc_msg.trailing.split(' ')
        names = self.names.get(irc_msg.channel)
        if names is None:
            self.names[irc_msg.channel] = new_names
        else:
            self.names[irc_msg.channel] = list(names) + new_names

    def end_names(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.names[irc_msg.channel] = tuple(self.names[irc_msg.channel])
        if self.is_channel_ready(irc_msg.channel):
            self.call_channel_ready_callback(irc_msg.channel)

    def pop_names(
            self,
            channel_login: str
    ) -> Tuple[str]:
        return tuple(self.names.pop(channel_login))

    def update_commands(
            self,
            irc_msg: IRCMessage
    ):
        raw_cmds = irc_msg.trailing.split(': ', 1)[1]
        raw_cmds = raw_cmds.split(' More', 1)[0]  # remove 'More help: https://help.twitch.tv/s/article/chat-commands'
        cmds = tuple(raw_cmds.split(' '))
        saved_cmds = self.commands.get(irc_msg.channel, ())
        cmds = tuple(set(saved_cmds) | set(cmds))  # remove dupls
        self.commands[irc_msg.channel] = cmds
        if self.is_channel_ready(irc_msg.channel):
            self.call_channel_ready_callback(irc_msg.channel)

    def is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        try:
            assert isinstance(self.channel_states.get(channel_login), IRCMessage)
            assert isinstance(self.client_states.get(channel_login), LocalState)
            assert isinstance(self.names.get(channel_login), tuple)
            if self.should_accum_commands:
                assert channel_login in self.commands
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
        local_state = self.client_states.pop(channel_login)
        names = self.names.pop(channel_login)
        commands = self.commands.pop(channel_login, ())
        return Channel(room_state, local_state, names, commands, self.send_callback)


class AnonChannelsAccumulator(ChannelsAccumulator):
    def is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        try:
            assert isinstance(self.channel_states.get(channel_login), IRCMessage)
            assert isinstance(self.names.get(channel_login), tuple)
        except AssertionError:
            return False
        else:
            self.client_states[channel_login] = LocalState(IRCMessage.create_empty())  # no userstate for no-user
            return True
