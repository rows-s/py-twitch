from abcs import AbstractMessage
from irc_channel import Channel
from irc_member import Member
from utils import replace_slashes

from typing import Dict, Optional


__all__ = (
    'Message',
    'ParentMessage'
)


class Message(AbstractMessage):
    def __init__(self,
                 channel: Channel,
                 author: Member,
                 content: str,
                 tags: Dict[str, str]) -> None:
        super().__init__(channel, author, content, tags)
        # variable tags
        self.bits = int(tags.get('bits', '0'))
        self.msg_id: Optional[str] = tags.get('msg-id')
        self.custom_reward_id: Optional[str] = tags.get('custom-reward-id')
        # parent message
        self.parent: Optional[ParentMessage]
        self.parent = ParentMessage(self.channel, tags) if ('reply-parent-display-name' in tags) else None

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')


class ParentMessage:
    def __init__(self, channel: Channel, tags: Dict[str, str]) -> None:
        self.channel: Channel = channel
        self.author_display_name = tags.get('reply-parent-display-name')
        self.author_login: str = tags.get('reply-parent-user-login')
        self.author_id: str = tags.get('reply-parent-user-id')
        self.content: str = replace_slashes(tags.get('reply-parent-msg-body', ''))
        self.id: str = tags.get('reply-parent-msg-id')

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')
