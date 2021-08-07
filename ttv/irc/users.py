from .channel import Channel
from .irc_message import IRCMessage
from .user_states import BaseState, LocalState, GlobalState

from abc import ABC
from typing import Callable, Coroutine

__all__ = ('BaseUser', 'ChannelUser', 'GlobalUser', 'ParentMessageUser')

# TODO: Must be Callable[[str, str, ..., Arg(str, name='agent')], Coroutine]
#  basing on Client.send_whisper(self, target: str, content: str, *, agent: str = None)
SendWhisperCallable = Callable[..., Coroutine]


class BaseUser(BaseState, ABC):
    """TODO"""
    def __init__(
            self,
            irc_msg: IRCMessage,
            send_whisper_callback: SendWhisperCallable
    ):
        super(BaseUser, self).__init__(irc_msg)
        self._send_whisper_callback: SendWhisperCallable = send_whisper_callback

    async def send_whisper(
            self,
            content: str
    ) -> None:
        await self._send_whisper_callback(self.login, content)


class ChannelUser(BaseUser, LocalState):
    """TODO"""
    def __init__(
            self, 
            irc_msg: IRCMessage, 
            channel: Channel, 
            send_wishper_callback: SendWhisperCallable
    ) -> None:
        super().__init__(irc_msg, send_wishper_callback)
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
            irc_msg: IRCMessage,
            send_whisper_callback: SendWhisperCallable
    ):
        self.id = irc_msg.tags.pop('reply-parent-user-id')
        self.login = irc_msg.tags.pop('reply-parent-user-login')
        self.display_name = irc_msg.tags.pop('reply-parent-display-name')
        self._send_whisper_callback: SendWhisperCallable = send_whisper_callback

    async def send_whisper(
            self,
            content: str
    ) -> None:
        await self._send_whisper_callback(self.login, content)
