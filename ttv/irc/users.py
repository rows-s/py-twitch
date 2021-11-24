from abc import ABC
from typing import Callable, Coroutine

from .channel import Channel
from .irc_connections import TwitchIRCClient
from .irc_messages import TwitchIRCMsg
from .user_states import BaseState, LocalState, GlobalState

__all__ = ('BaseUser', 'ChannelUser', 'GlobalUser', 'ParentMessageUser')

SendWhisperCallable = Callable[[str, str], Coroutine]


class BaseUser(BaseState, ABC):
    """TODO"""
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            irc_conn: TwitchIRCClient,
    ):
        super().__init__(irc_msg)
        self._irc_conn: TwitchIRCClient = irc_conn

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
            irc_conn: TwitchIRCClient,
    ) -> None:
        super().__init__(irc_msg, irc_conn)
        self.channel: Channel = channel

    async def ban(self, reason: str = ''):
        await self.channel.send_message(f'/ban {self.login} {reason}')

    async def unban(self):
        await self.channel.send_message(f'/unban {self.login}')

    async def timeout(self, seconds: int):
        await self.channel.send_message(f'/timeout {self.login} {seconds}')

    async def untimeout(self):
        await self.channel.send_message(f'/untimeout  {self.login}')

    async def vip(self):
        await self.channel.send_message(f'/vip {self.login}')

    async def unvip(self):
        await self.channel.send_message(f'/unvip {self.login}')

    async def mod(self):
        await self.channel.send_message(f'/mod {self.login}')

    async def unmod(self):
        await self.channel.send_message(f'/unmod {self.login}')


class GlobalUser(BaseUser, GlobalState):
    """TODO"""


class ParentMessageUser:
    """TODO"""
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            irc_conn: TwitchIRCClient,
    ):
        self.id = irc_msg.tags.pop('reply-parent-user-id')
        self.login = irc_msg.tags.pop('reply-parent-user-login')
        self.display_name = irc_msg.tags.pop('reply-parent-display-name')
        self._irc_conn: TwitchIRCClient = irc_conn

    async def send_whisper(
            self,
            content: str
    ) -> None:
        await self._irc_conn.send_whisper(self.login, content)
