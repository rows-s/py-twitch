from abc import ABC

from .irc_message import IRCMessage
from .channel import Channel
from .flags import Flag
from .emotes import Emote
from .users import BaseUser, ChannelUser, ParentMessageUser, GlobalUser
from .utils import parse_raw_emotes, is_emote_only, parse_raw_flags

from typing import Optional,  List

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
            author: BaseUser
    ) -> None:
        # prepared
        self.author: BaseUser = author
        self.content: str = irc_msg.content
        # stable tags
        self.id: str = irc_msg.tags.get('id')
        self.time: int = int(irc_msg.tags.get('tmi-sent-ts', 0))
        self.flags: List[Flag] = parse_raw_flags(irc_msg.tags.get('flags'), irc_msg.content)
        # emotes
        self.emote_only: bool = irc_msg.tags.get('emote-only') == '1'
        self.emotes: List[Emote] = parse_raw_emotes(irc_msg.tags.get('emotes', ''), irc_msg.content)

    def __str__(self):
        return f'@{self.author.login} :{self.content}'


class ParentMessage:
    def __init__(
            self,
            irc_msg: IRCMessage,
            channel: Channel,
            author: ParentMessageUser
    ) -> None:
        self.channel: Channel = channel
        self.author: ParentMessageUser = author
        self.content: str = irc_msg.tags.get('reply-parent-msg-body')
        self.id: str = irc_msg.tags.get('reply-parent-msg-id')

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')

    def __str__(self):
        return f'@{self.author.login} to #{self.channel.login} :{self.content}'


class ChannelMessage(BaseMessage):
    def __init__(
            self,
            irc_msg: IRCMessage,
            channel: Channel,
            author: ChannelUser
    ) -> None:
        super().__init__(irc_msg, author)
        # variable tags
        self.channel: Channel = channel
        self.bits: int = int(irc_msg.tags.get('bits', 0))
        self.msg_id: Optional[str] = irc_msg.tags.get('msg-id')
        self.custom_reward_id: Optional[str] = irc_msg.tags.get('custom-reward-id')
        # parent message
        self.parent_message: Optional[ParentMessage] = self._crate_parent_message(irc_msg.copy())

    @property
    def is_reply(self):
        return self.parent_message is not None

    def __str__(self):
        return f'@{self.author.login} to #{self.channel.login} :{self.content}'

    def _crate_parent_message(
            self,
            irc_msg: IRCMessage
    ) -> Optional[ParentMessage]:
        if 'reply-parent-msg-id' in irc_msg.tags:
            # TODO: Could be better than take private field... but how?
            author = ParentMessageUser(irc_msg.copy(), self.author._send_whisper_callback)
            return ParentMessage(irc_msg.copy(), self.channel, author)
        else:
            return None

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
