from .irc_message import IRCMessage
from .user_states import LocalState

from typing import Callable, Tuple, Coroutine

__all__ = ('Channel',)


class Channel:
    def __init__(
            self,
            irc_msg: IRCMessage,
            client_state: LocalState,
            names: Tuple[str, ...],
            commands: Tuple[str, ...],
            mods: Tuple[str, ...],
            vips: Tuple[str, ...],
            _send_callback: Callable[[str], Coroutine]
    ) -> None:
        self._irc_msg: IRCMessage = irc_msg
        self.client_state: LocalState = client_state
        # TODO: logically the class must not have this variable (client_state),
        #  because it represents state of a :class:`Client` not anything of :class:`Channel`.
        #  But that way's easier to understand and to use
        self.names: Tuple[str, ...] = names
        self.commands: Tuple[str, ...] = commands
        self.mods: Tuple[str, ...] = mods
        self.vips: Tuple[str, ...] = vips
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
        return self.__class__(
            self._irc_msg.copy(), self.client_state, self.names, self.commands, self.mods, self.vips, self._send
        )

    async def send_message(
            self,
            content: str
    ) -> None:
        await self._send(f'PRIVMSG #{self.login} :{content}')

    async def request_state_update(self):
        await self._send(f'JOIN #{self.login}')

    async def request_commands(self):
        await self.send_message('/help')

    async def request_mods(self):
        await self.send_message('/mods')

    async def request_vips(self):
        await self.send_message('/vips')

    async def clear(self):
        await self.send_message('/clear')

    def __eq__(self, other):
        if isinstance(other, Channel):
            return self._irc_msg == other._irc_msg
        return False


