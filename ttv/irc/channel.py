from .irc_message import IRCMessage
from .user_states import LocalState

from typing import Callable, Iterable, Optional

__all__ = ('Channel',)


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


class ChannelParts:
    def __init__(self):
        self.irc_msg: Optional[IRCMessage] = None
        self.local_state: Optional[LocalState] = None
        self.names: Optional[Iterable[str]] = None

    def is_ready(self):
        return all((
            isinstance(self.irc_msg, IRCMessage),
            isinstance(self.local_state, LocalState),
            isinstance(self.names, tuple)
        ))

    def create_channel(self, send_callback: Callable) -> Channel:
        return Channel(self.irc_msg, self.local_state, self.names, send_callback)
