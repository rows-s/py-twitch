from .channel import Channel
from .irc_message import IRCMessage
from .user_states import BaseState, BaseLocalState
from .utils import parse_raw_badges

from abc import ABC
from typing import Dict, Optional, Callable


__all__ = ('BaseUser', 'ChannelMember', 'GlobalUser', 'ParentMessageUser')


class BaseUser(BaseState, ABC):
    def __init__(
            self,
            irc_msg: IRCMessage,
            send_whisper_callback: Callable
    ):
        super(BaseUser, self).__init__(irc_msg)
        self._send_whisper_callback: Callable = send_whisper_callback

    async def send_whisper(
            self,
            content: str,
            *,
            agent: str = None
    ) -> None:
        await self._send_whisper_callback(self.login, content, agent=agent)


class ChannelMember(BaseUser, BaseLocalState):
    def __init__(
            self, 
            irc_msg: IRCMessage, 
            channel: Channel, 
            send_wishper_callback: Callable
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
        await self.channel.send_message(f'/timeout {self.login} 1')

    async def vip(self):
        await self.channel.send_message(f'/vip {self.login}')

    async def unvip(self):
        await self.channel.send_message(f'/unvip {self.login}')

    async def mod(self):
        await self.channel.send_message(f'/mod {self.login}')

    async def unmod(self):
        await self.channel.send_message(f'/unmod {self.login}')


class GlobalUser(BaseUser):
    pass


class ParentMessageUser(BaseUser):
    def __init__(
            self,
            irc_msg: IRCMessage,
            send_whisper_callback: Callable
    ):
        irc_msg.tags = {
            'user-id': irc_msg.tags.get('reply-parent-user-id'),
            'user-login': irc_msg.tags.get('reply-parent-user-login'),
            'display-name': irc_msg.tags.get('reply-parent-display-name'),
        }
        super().__init__(irc_msg, send_whisper_callback)
