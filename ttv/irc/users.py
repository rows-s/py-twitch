from .channel import Channel
from .utils import parse_raw_badges

from abc import ABC
from typing import Dict, Optional, Callable


__all__ = (
    'UserABC',
    'ChannelMember',
    'GlobalUser',
    'ParentMessageUser'
)


class UserABC(ABC):
    def __init__(
            self,
            tags: Dict[str, str],
            send_whisper_callback: Callable
    ):
        self.id: str = tags.get('user-id')
        self.login: str = tags.get('user-login')
        self.display_name: str = tags.get('display-name')
        self.color: str = tags.get('color')
        self.badges: Dict[str, str] = parse_raw_badges(tags.get('badges', ''))
        # callback
        self._send_whisper_callback: Callable = send_whisper_callback

    async def send_whisper(
            self,
            content: str,
            *,
            agent: str = None
    ) -> None:
        await self._send_whisper_callback(self.login, content, agent=agent)


class ChannelMember(UserABC):
    def __init__(self, tags: Dict[str, str], channel: Channel, send_wishper_callback: Callable) -> None:
        super().__init__(tags, send_wishper_callback)
        # prepared
        self.channel: Channel = channel
        # variable tags
        self.client_nonce: Optional[str] = tags.get('client-nonce')
        self.badge_info: Dict[str, str] = parse_raw_badges(tags.get('badge-info', ''))
        # local roles
        self.is_broadcaster: bool = 'broadcaster' in self.badges
        self.is_moderator: bool = 'moderator' in self.badges
        self.is_sub_gifter: bool = 'sub-gifter' in self.badges
        self.is_subscriber: bool = 'subscriber' in self.badges
        self.is_cheerer: bool = 'bits' in self.badges
        self.is_vip: bool = 'vip' in self.badges
        # roles values
        self.gifted_subs_count: int = int(self.badges.get('sub-gifter', 0))
        self.subscribed_mounths: int = int(self.badge_info.get('subscriber', 0))
        self.bits: int = int(self.badges.get('bits', 0))

    async def ban(self, reason: str = ''):
        command = f'/ban {self.login} {reason}'
        await self.channel.send_message(command)

    async def unban(self):
        command = f'/unban {self.login}'
        await self.channel.send_message(command)

    async def timeout(self, seconds: int):
        command = f'/timeout {self.login} {seconds}'
        await self.channel.send_message(command)

    async def untimeout(self):
        command = f'/timeout {self.login} 1'
        await self.channel.send_message(command)

    async def vip(self):
        command = f'/vip {self.login}'
        await self.channel.send_message(command)

    async def unvip(self):
        command = f'/unvip {self.login}'
        await self.channel.send_message(command)

    async def mod(self):
        command = f'/mod {self.login}'
        await self.channel.send_message(command)

    async def unmod(self):
        command = f'/unmod {self.login}'
        await self.channel.send_message(command)


class GlobalUser(UserABC):
    pass


class ParentMessageUser(UserABC):
    def __init__(
            self,
            tags,
            send_whisper_callback: Callable
    ):
        # TODO: to create a new dict with new keys seems as a good action.
        #  Because we don't need to add expressions in code.
        #  But maybe can be better?
        new_tags = {
            'user-id': tags['reply-parent-user-id'],
            'user-login': tags['reply-parent-user-login'],
            'display-name': tags['reply-parent-display-name'],
        }
        super().__init__(new_tags, send_whisper_callback)
