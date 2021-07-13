from abc import ABC

from .channel import Channel
from .users import UserABC, ChannelMember, ParentMessageUser, GlobalUser
from .utils import unescape_tag_value, parse_raw_emotes, is_emote_only

from typing import Dict, Optional, Tuple, List

__all__ = (
    'BaseMessage',
    'ChannelMessage',
    'ParentMessage',
    'WhisperMessage'
)


class BaseMessage(ABC):
    def __init__(
            self,
            author: UserABC,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        # prepared
        self.author: UserABC = author
        self.content: str = content
        # stable tags
        self.id: str = tags.get('id')
        self.time: int = int(tags.get('tmi-sent-ts', 0))
        self.flags: str = tags.get('flags')
        # emotes
        self.emote_only: bool = tags.get('emote-only') == '1'
        self.emotes: Dict[str, List[Tuple[int, int]]] = parse_raw_emotes(tags.get('emotes', ''))


class ParentMessage:
    def __init__(
            self,
            channel: Channel,
            author: ParentMessageUser,
            tags: Dict[str, str]
    ) -> None:
        self.channel: Channel = channel
        self.author = author
        self.content: str = unescape_tag_value(tags.get('reply-parent-msg-body', ''))
        self.id: str = tags.get('reply-parent-msg-id')

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')


class ChannelMessage(BaseMessage):
    def __init__(
            self,
            channel: Channel,
            author: ChannelMember,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, content, tags)
        # variable tags
        self.channel: Channel = channel
        self.bits = int(tags.get('bits', '0'))
        self.msg_id: Optional[str] = tags.get('msg-id')
        self.custom_reward_id: Optional[str] = tags.get('custom-reward-id')
        # parent message
        self.is_reply: bool = 'reply-parent-msg-id' in tags
        if self.is_reply:
            self.parent_message: Optional[ParentMessage] = self._get_parent_message(tags)
        else:
            self.parent_message: Optional[ParentMessage] = None

    def _get_parent_message(self, tags: Dict[str, str]) -> Optional[ParentMessage]:
        # TODO: Is not the best way just take the `send_wishper_callback` from `self.author` . Better improve.
        parent_message_author: ParentMessageUser = ParentMessageUser(tags, self.author._send_wishper_callback)
        return ParentMessage(self.channel, parent_message_author, tags)

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')


class WhisperMessage(BaseMessage):
    def __init__(
            self,
            author: GlobalUser,
            content: str,
            tags: Dict[str, str]
    ):
        tags = tags.copy()  # side effects
        tags['id'] = tags['message-id']  # rename the field
        super().__init__(author, content, tags)
        self.thread_id = tags.get('thread-id')
        self.emote_only: bool = is_emote_only(content, self.emotes)
