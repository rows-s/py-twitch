from abc import ABC

from .irc_message import IRCMessage
from .channel import Channel
from .users import UserABC, ChannelMember, ParentMessageUser, GlobalUser
from .utils import parse_raw_emotes, is_emote_only

from typing import Dict, Optional, Tuple, List

__all__ = (
    'BaseMessage',
    'ChannelMessage',
    'ParentMessage',
    'Whisper'
)


class BaseMessage(ABC):
    def __init__(
            self,
            irc_msg: IRCMessage,
            author: UserABC
    ) -> None:
        # prepared
        self.author: UserABC = author
        self.content: str = irc_msg.content
        # stable tags
        self.id: str = irc_msg.tags.get('id')
        self.time: int = int(irc_msg.tags.get('tmi-sent-ts', 0))
        self.flags: str = irc_msg.tags.get('flags')
        # emotes
        self.emote_only: bool = irc_msg.tags.get('emote-only') == '1'
        self.emotes: Dict[str, List[Tuple[int, int]]] = parse_raw_emotes(irc_msg.tags.get('emotes', ''))


class ParentMessage:
    def __init__(
            self,
            irc_msg: IRCMessage,
            channel: Channel,
            author: ParentMessageUser
    ) -> None:
        self.channel: Channel = channel
        self.author = author
        self.content: str = irc_msg.tags.get('reply-parent-msg-body', '')
        self.id: str = irc_msg.tags.get('reply-parent-msg-id')

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')


class ChannelMessage(BaseMessage):
    def __init__(
            self,
            irc_msg: IRCMessage,
            channel: Channel,
            author: ChannelMember
    ) -> None:
        super().__init__(irc_msg, author)
        # variable tags
        self.channel: Channel = channel
        self.bits = int(irc_msg.tags.get('bits', '0'))
        self.msg_id: Optional[str] = irc_msg.tags.get('msg-id')
        self.custom_reward_id: Optional[str] = irc_msg.tags.get('custom-reward-id')
        # parent message
        self.is_reply: bool = 'reply-parent-msg-id' in irc_msg.tags
        if self.is_reply:
            self.parent_message: Optional[ParentMessage] = self._get_parent_message(irc_msg)
        else:
            self.parent_message: Optional[ParentMessage] = None

    def _get_parent_message(
            self,
            irc_msg: IRCMessage
    ) -> Optional[ParentMessage]:
        # TODO: Is not the best way just take the `send_whisper_callback` from `self.author` . Better improve.
        parent_message_author: ParentMessageUser = ParentMessageUser(irc_msg.tags, self.author._send_whisper_callback)
        return ParentMessage(irc_msg, self.channel, parent_message_author)

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')


class Whisper(BaseMessage):
    def __init__(
            self,
            irc_msg: IRCMessage,
            author: GlobalUser
    ):
        irc_msg.tags['id'] = irc_msg.tags['message-id']  # rename the field
        super().__init__(irc_msg, author)
        self.thread_id = irc_msg.tags.get('thread-id')
        self.emote_only: bool = is_emote_only(irc_msg.content, self.emotes)
