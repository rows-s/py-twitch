from abc import ABC

from irc_channel import Channel
from irc_users import UserABC, ChannelMember, ParentMessageUser, GlobalUser
from utils import replace_slashes, parse_raw_emotes

from typing import Dict, Optional, Tuple, List

__all__ = (
    'MessageABC',
    'ChannelMessage',
    'ParentMessage',
    'WhisperMessage'
)


class MessageABC(ABC):
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
        self.time: int = int(tags.get('tmi-sent-ts', '0'))
        self.flags: str = tags.get('flags')
        # emotes
        self.emote_only: bool = tags.get('emote-only') == '1'
        self.emotes: Dict[str, List[Tuple[int, int]]] = parse_raw_emotes(tags.get('emotes', ''))


class WhisperMessage(MessageABC):
    def __init__(
            self,
            author: GlobalUser,
            content: str,
            tags: Dict[str, str]
    ):
        tags['id'] = tags['message-id']  # rename the field
        super().__init__(author, content, tags)
        emotes_count: int = 0
        emotes_length: int = 0
        for positions in self.emotes.values():
            emotes_count += len(positions)
            for start, end in positions:
                emotes_length += end - start + 1
        # if length of all emotes + count of space between each emote is greater than all content -> is emotes only
        self.emote_only = emotes_length + emotes_count - 1 == len(self.content)
        self.thread_id = tags.get('thread-id')


class ChannelMessage(MessageABC):
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
            # TODO: Is not the best way just take the `send_wishper_callback` from self.author. Better improve.
            parent_message_author: ParentMessageUser = ParentMessageUser(tags, self.author._send_wishper_callback)
            self.parent_message: Optional[ParentMessage]
            self.parent_message = ParentMessage(self.channel, parent_message_author, tags)
        else:
            self.parent_message = None
        self.is_reply: bool = self.parent_message is not None

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')


class ParentMessage:
    def __init__(
            self,
            channel: Channel,
            author: ParentMessageUser,
            tags: Dict[str, str]
    ) -> None:
        self.channel: Channel = channel
        self.author = author
        self.content: str = replace_slashes(tags.get('reply-parent-msg-body', ''))
        self.id: str = tags.get('reply-parent-msg-id')

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')
