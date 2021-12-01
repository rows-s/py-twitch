from abc import ABC
from typing import Callable, Coroutine

from .channel import Channel
from .irc_connections import TTVIRCClient
from .irc_messages import TwitchIRCMsg
from .user_states import BaseState, LocalState, GlobalState

__all__ = ('BaseUser', 'ChannelUser', 'GlobalUser', 'ParentMessageUser')

SendWhisperCallable = Callable[[str, str], Coroutine]


class BaseUser(BaseState, ABC):
    """TODO"""
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            irc_conn: TTVIRCClient,
    ):
        super().__init__(irc_msg)
        self._irc_conn: TTVIRCClient = irc_conn

    async def send_whisper(
            self,
            content: str
    ) -> None:
        await self._irc_conn.send_whisper(self.login, content)


class ChannelUser(BaseUser, LocalState):
    """TODO"""
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            channel: Channel,
            irc_conn: TTVIRCClient,
    ) -> None:
        super().__init__(irc_msg, irc_conn)
        self.channel: Channel = channel

    async def ban(self, reason: str = ''):
        await self.channel.send(f'/ban {self.login} {reason}')

    async def unban(self):
        await self.channel.send(f'/unban {self.login}')

    async def timeout(self, seconds: int):
        await self.channel.send(f'/timeout {self.login} {seconds}')

    async def untimeout(self):
        await self.channel.send(f'/untimeout  {self.login}')

    async def vip(self):
        await self.channel.send(f'/vip {self.login}')

    async def unvip(self):
        await self.channel.send(f'/unvip {self.login}')

    async def mod(self):
        await self.channel.send(f'/mod {self.login}')

    async def unmod(self):
        await self.channel.send(f'/unmod {self.login}')


class GlobalUser(BaseUser, GlobalState):
    """TODO"""


class ParentMessageUser:
    """TODO"""
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            irc_conn: TTVIRCClient,
    ):
        self.id = irc_msg.tags.pop('reply-parent-user-id')
        self.login = irc_msg.tags.pop('reply-parent-user-login')
        self.display_name = irc_msg.tags.pop('reply-parent-display-name')
        self._irc_conn: TTVIRCClient = irc_conn

    async def send_whisper(
            self,
            content: str
    ) -> None:
        await self._irc_conn.send_whisper(self.login, content)
