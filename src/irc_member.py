from typing import Dict, Optional
from irc_channel import Channel
from utils import badges_to_dict


class Member:
    def __init__(self, 
                 channel: Channel,
                 tags: Dict[str, str]) -> None:

        self.channel = channel
        self.id: int = int(tags['user-id'])
        self.name: str = tags['display-name']
        self.color: str = tags['color']

        self.badges: Dict[str, str] = badges_to_dict(tags['badges'])
        self.badges_info: Dict[str, str] = badges_to_dict(tags['badge-info'])

        self.admin = True if 'admin' in self.badges else False
        self.mod = True if 'moderator' in self.badges else False
        self.broadcaster = True if 'broadcaster' in self.badges else False
        self.bits = int(self.badges['bits']) if 'bits' in self.badges else 0
        self.subscriber = int(self.badges['subscriber']) if 'subscriber' in self.badges else 0
        self.client_nonce: Optional[str] = tags['client-nonce'] if 'client-nonce' in tags else None
    
    async def whisper(self, content: str) -> str:
        command = f'/w {self.name} {content}'
        await self.channel.send(command)
        return command

    async def ban(self, reason: str = '') -> str:
        command = f'/ban {self.name} {reason}'
        await self.channel.send(command)
        return command

    async def timeout(self, seconds: int) -> str:
        command = f'/timeout {self.name} {seconds}'
        await self.channel.send(command)
        return command
    
    async def unban(self) -> str:
        command = f'/unban {self.name}'
        await self.channel.send(command)
        return command

    async def vip(self) -> str:
        command = f'/vip {self.name}'
        await self.channel.send(command)
        return command

    async def unvip(self) -> str:
        command = f'/unvip {self.name}'
        await self.channel.send(command)
        return command

    async def mod(self) -> str:
        command = f'/mod {self.name}'
        await self.channel.send(command)
        return command

    async def unmod(self) -> str:
        command = f'/unmod {self.name}'
        await self.channel.send(command)
        return command
