from typing import Dict, Optional
from irc_channel import Channel
from utils import parse_raw_badges


__all__ = ['Member']


class Member:
    def __init__(
            self,
            channel: Channel,
            tags: Dict[str, str]
    ) -> None:
        # prepared
        self.channel: Channel = channel
        # stable tags
        self.id: str = tags.get('user-id')
        self.login: str = tags.get('login')
        self.display_name: str = tags.get('display-name')
        self.color: str = tags.get('color')
        # variable tags
        self.client_nonce: Optional[str] = tags.get('client-nonce')
        # badges
        self.badges: Dict[str, str] = parse_raw_badges(tags.get('badges', ''))
        self.badge_info: Dict[str, str] = parse_raw_badges(tags.get('badge-info', ''))
        # local roles
        self.is_broadcaster: bool = 'broadcaster' in self.badges
        self.is_moderator: bool = 'moderator' in self.badges
        self.is_sub_gifter: bool = 'sub-gifter' in self.badges
        self.is_subscriber: bool = 'subscriber' in self.badges
        self.is_cheerer: bool = 'bits' in self.badges
        self.is_vip: bool = 'vip' in self.badges
        # roles values
        self.sub_gifter_count: int = int(self.badges.get('sub-gifter', '0'))
        self.subscriber_mounths: int = int(self.badge_info.get('subscriber', '0'))
        self.bits: int = int(self.badges.get('bits', '0'))
    
    async def whisper(self, content: str):
        command = f'/w {self.login} {content}'
        await self.channel.send_message(command)

    async def ban(self, reason: str = ''):
        command = f'/ban {self.login} {reason}'
        await self.channel.send_message(command)

    async def timeout(self, seconds: int):
        command = f'/timeout {self.login} {seconds}'
        await self.channel.send_message(command)
    
    async def unban(self):
        command = f'/unban {self.login}'
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
