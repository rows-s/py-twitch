from typing import Tuple

from .irc_connections import TTVIRCClient
from .irc_messages import TwitchIRCMsg
from .user_states import LocalState

__all__ = ('Channel',)


class Channel:
    def __init__(
            self,
            raw_state: TwitchIRCMsg,
            client_state: LocalState,
            names: Tuple[str, ...],
            commands: Tuple[str, ...],
            mods: Tuple[str, ...],
            vips: Tuple[str, ...],
            irc_conn: TTVIRCClient
    ) -> None:
        self.id: str = raw_state.get('room-id')
        self.login: str = raw_state.channel
        # TODO: logically the class must not have this variable (client_state),
        #  because it represents state of a :class:`Client` not anything of :class:`Channel`.
        #  But that way's easier to understand and to use
        self.client_state: LocalState = client_state
        self.names: Tuple[str, ...] = names
        self.commands: Tuple[str, ...] = commands
        self.mods: Tuple[str, ...] = mods
        self.vips: Tuple[str, ...] = vips
        self._raw_state: TwitchIRCMsg = raw_state
        self._irc_conn: TTVIRCClient = irc_conn

    @property
    def is_unique_only(self) -> bool:
        return self._raw_state.get('r9k') == '1'

    @property
    def is_emote_only(self) -> bool:
        return self._raw_state.get('emote-only') == '1'

    @property
    def is_subs_only(self) -> bool:
        return self._raw_state.get('subs-only') == '1'

    @property
    def has_rituals(self) -> bool:
        return self._raw_state.get('rituals') == '1'

    @property
    def slow_seconds(self) -> int:
        return int(self._raw_state.get('slow', 0))

    @property
    def is_slow(self) -> bool:
        return self.slow_seconds != 0

    @property
    def followers_only_minutes(self) -> int:
        return int(self._raw_state.get('followers-only', 0))

    @property
    def is_followers_only(self) -> bool:
        return self.followers_only_minutes != -1

    def update_state(
            self,
            irc_msg: TwitchIRCMsg
    ):
        """
        Updates state-attributes with new values provided in :arg:`irc_msg`.

        Notes:
            Does not change a value if there isn't the value in `irc_msg`.
        Args:
            irc_msg :class:`TwitchIRCMsg`:
                 TwitchIRCMsg with new values
        """
        self._raw_state.update(irc_msg)

    def copy(self):
        return self.__class__(
            self._raw_state.copy(), self.client_state, self.names, self.commands, self.mods, self.vips, self._irc_conn
        )

    async def send(
            self,
            content: str
    ) -> None:
        await self._irc_conn.send_msg(self.login, content)

    async def request_state_update(self):
        await self._irc_conn.join_channels(self.login)

    async def request_commands(self):
        await self.send('/help')

    async def request_mods(self):
        await self.send('/mods')

    async def request_vips(self):
        await self.send('/vips')

    async def clear(self):
        await self.send('/clear')

    def __eq__(self, other):
        return isinstance(other, Channel) and self.login == other.login
