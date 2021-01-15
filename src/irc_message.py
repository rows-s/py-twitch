from irc_channel import Channel
from irc_member import Member
from typing import Dict, List, Optional
from utils import emotes_to_dict, replace


class Message:
    def __init__(self,
                 channel: Channel,
                 author: Member,
                 content: str,
                 tags: Dict[str, str]) -> None:

        self.channel: Channel = channel
        self.author: Member = author
        self.content: str = content
        self.id: str = tags['id']
        self.flags: str = tags['flags']
        self.time: int = int(tags['tmi-sent-ts'])
        self.emotes: Dict[str, List[int]] = emotes_to_dict(tags['emotes'])
        self.emote_only: bool = True if ('emote-only' in tags) else False
        self.bits = int(tags['bits']) if 'bits' in tags else 0
        if 'reply-parent-display-name' in tags:
            self.parent: Optional[Message.ParentMessage] = self.ParentMessage(self.channel, tags)
        else:
            self.parent = None

    async def delete(self) -> str:
        command = f'/delete {self.id}'
        await self.channel.send(command)
        return command

    class ParentMessage:
        def __init__(self, channel: Channel, tags: Dict[str, str]) -> None:
            self.channel: Channel = channel
            self.author_name: str = tags['reply-parent-user-login']
            self.author_id: int = int(tags['reply-parent-user-id'])
            self.content: str = replace(tags['reply-parent-msg-body'])
            self.id: str = tags['reply-parent-msg-id']

        async def delete(self) -> str:
            command = f'/delete {self.id}'
            await self.channel.send(command)
            return command
