from copy import copy

from .irc_message import IRCMessage
from .user_states import LocalState

from typing import Callable, Iterable, Optional, Dict, Union, List, Tuple, Coroutine

__all__ = ('Channel', 'ChannelsAccumulator')


class Channel:
    def __init__(
            self,
            irc_msg: IRCMessage,
            local_state: LocalState,
            names: Tuple[str],
            _send_callback: Callable
    ) -> None:
        self.irc_msg: IRCMessage = irc_msg
        self.local_state: LocalState = local_state
        # TODO: logically the class must not have this variable (local_state),
        #  because it represents state of a IRCUser not anything of IRCChannel.
        #  But that way's easier to understand and to use
        self.names: Tuple[str] = names
        self._send: Callable = _send_callback

    @property
    def id(self) -> str:
        return self.irc_msg.tags.get('room-id')

    @property
    def login(self) -> str:
        return self.irc_msg.tags.get('room-login')

    @property
    def is_unique_only(self) -> bool:
        return self.irc_msg.tags.get('r9k') == '1'

    @property
    def is_emote_only(self) -> bool:
        return self.irc_msg.tags.get('emote-only') == '1'

    @property
    def is_subs_only(self) -> bool:
        return self.irc_msg.tags.get('subs-only') == '1'

    @property
    def has_rituals(self) -> bool:
        return self.irc_msg.tags.get('rituals') == '1'

    @property
    def slow_seconds(self) -> int:
        return int(self.irc_msg.tags.get('slow', 0))

    @property
    def is_slow(self) -> bool:
        return self.slow_seconds != 0

    @property
    def followers_only_minutes(self) -> int:
        return int(self.irc_msg.tags.get('followers-only', 0))

    @property
    def is_followers_only(self) -> bool:
        return self.followers_only_minutes != -1

    def update_state(self, tags: Dict[str, Optional[str]]):
        self.irc_msg.tags.update(tags)

    async def send_message(
            self,
            conntent: str
    ) -> None:
        await self._send(f'PRIVMSG #{self.login} :{conntent}')

    async def update(self):
        await self._send(f'JOIN #{self.login}')

    async def clear(self):
        await self.send_message('/clear')

    def copy(self):
        local_state = copy(self.local_state)
        names = self.names
        return self.__class__(self.irc_msg.copy(), local_state, names, self._send)


class ChannelsAccumulator:
    def __init__(
            self,
            channel_ready_callback: Callable[[Channel], None],
            send_callback: Callable[[str], Coroutine]
    ) -> None:
        self.room_states: Dict[str, IRCMessage] = {}
        self.local_states: Dict[str, LocalState] = {}
        self.names: Dict[str, Union[List[str], Tuple[str]]] = {}
        self.channel_ready_callback: Callable[[Channel], None] = channel_ready_callback
        self.send_callback: Callable[[str], Coroutine] = send_callback

    def add_room_state(
            self,
            state: IRCMessage
    ) -> None:
        self.room_states[state.channel] = state

    def update_room_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        room_state = self.room_states.get(irc_msg.channel)
        if room_state is None:
            self.room_states[irc_msg.channel] = irc_msg
        else:
            room_state.tags.update(irc_msg.tags)
        if self.is_channel_ready(irc_msg.channel):
            self.call_channel_ready_callback(irc_msg.channel)

    def add_local_state(
            self,
            irc_msg: IRCMessage
    ) -> None:
        self.local_states[irc_msg.channel] = LocalState(irc_msg.tags)
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
            names.extend(new_names)

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
    ) -> Union[List[str], Tuple[str]]:
        return self.names.pop(channel_login)

    def is_channel_ready(
            self,
            channel_login: str
    ) -> bool:
        return all((
            isinstance(self.room_states.get(channel_login), IRCMessage),
            isinstance(self.local_states.get(channel_login), LocalState),
            isinstance(self.names.get(channel_login), tuple)
        ))

    def call_channel_ready_callback(self, channel_login: str):
        self.channel_ready_callback(
            self.create_channel(channel_login)
        )

    def create_channel(
            self,
            channel_login: str
    ) -> Channel:
        room_state = self.room_states.pop(channel_login)
        local_state = self.local_states.pop(channel_login)
        names = self.names.pop(channel_login)
        return Channel(room_state, local_state, names, self.send_callback)
