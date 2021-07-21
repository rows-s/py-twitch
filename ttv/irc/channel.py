from .irc_message import IRCMessage
from .user_states import LocalState

from typing import Callable, Iterable, Optional, Dict, Union, List, Tuple, Coroutine

__all__ = ('Channel', 'ChannelsAccumulator')


class Channel:
    def __init__(
            self,
            irc_msg: IRCMessage,
            local_state: LocalState,
            names: Iterable[str],
            _send_callback: Callable
    ) -> None:
        self._tags = irc_msg.tags
        self.local_state = local_state
        # TODO: logically the class must not have this variable (local_stae),
        #  because it represents state of a IRCUser not anything of IRCChannel.
        #  But that way's easier to understand and to use
        self.names = names
        self._send: Callable = _send_callback

    @property
    def id(self) -> str:
        return self._tags.get('room-id')

    @property
    def login(self) -> str:
        return self._tags.get('room-login')

    @property
    def is_unique_only(self) -> bool:
        return self._tags.get('r9k') == '1'

    @property
    def is_emote_only(self) -> bool:
        return self._tags.get('emote-only') == '1'

    @property
    def is_subs_only(self) -> bool:
        return self._tags.get('subs-only') == '1'

    @property
    def has_rituals(self) -> bool:
        return self._tags.get('rituals') == '1'

    @property
    def slow_seconds(self) -> int:
        return int(self._tags.get('slow', 0))

    @property
    def is_slow(self) -> bool:
        return self.slow_seconds != 0

    @property
    def followers_only_minutes(self) -> int:
        return int(self._tags.get('followers-only', 0))

    @property
    def is_followers_only(self) -> bool:
        return self.followers_only_minutes != -1

    def update_state(self, irc_msg: IRCMessage):
        self._tags.update(irc_msg.tags)

    async def send_message(
            self,
            conntent: str
    ) -> None:
        await self._send(f'PRIVMSG #{self.login} :{conntent}')

    async def update(self):
        await self._send(f'JOIN #{self.login}')

    async def clear(self):
        await self.send_message('/clear')


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
            if self.is_channel_ready(irc_msg.channel):
                self.call_channel_ready_callback(irc_msg.channel)
        else:
            room_state.update_tags(irc_msg.tags)

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
            irc_msg: IRCMessage
    ) -> Union[List[str], Tuple[str]]:
        return self.names.pop(irc_msg.channel)

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
            self.create_channel(channel_login, self.send_callback)
        )

    def create_channel(
            self,
            channel_login: str,
            send_callback: Callable
    ) -> Channel:
        room_state = self.room_states.pop(channel_login)
        local_state = self.local_states.pop(channel_login)
        names = self.names.pop(channel_login)
        return Channel(room_state, local_state, names, send_callback)
