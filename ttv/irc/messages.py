from abc import ABC
from functools import cached_property
from typing import Optional, Tuple

from .channel import Channel
from .emotes import Emote
from .flags import Flag
from .irc_messages import TwitchIRCMsg
from .users import BaseUser, ChannelUser, ParentMessageUser, GlobalUser
from .utils import parse_raw_emotes, is_emote_only, parse_raw_flags

__all__ = (
    'BaseMessage',
    'ChannelMessage',
    'ParentMessage',
    'Whisper'
)


class BaseMessage(ABC):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: BaseUser
    ) -> None:
        self.author: BaseUser = author
        self.content: str = irc_msg.trailing
        self.id: str = irc_msg.get('id')
        self.timestamp: int = int(irc_msg.get('tmi-sent-ts', 0))
        self._raw_flags: str = irc_msg.get('flags', '')
        self.emote_only: bool = irc_msg.get('emote-only') == '1'
        self._raw_emotes: str = irc_msg.get('emotes', '')

    @cached_property
    def flags(self) -> Tuple[Flag]:
        return parse_raw_flags(self._raw_flags, self.content)

    @cached_property
    def emotes(self) -> Tuple[Emote]:
        return parse_raw_emotes(self._raw_emotes, self.content)

    def __str__(self):
        return f'@{self.author.login} :{self.content}'


class ParentMessage:
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            channel: Channel,
            author: ParentMessageUser
    ) -> None:
        self.channel: Channel = channel
        self.author: ParentMessageUser = author
        self.content: str = irc_msg.get('reply-parent-msg-body')
        self.id: str = irc_msg.get('reply-parent-msg-id')

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')

    def __str__(self):
        return f'@{self.author.login} to #{self.channel.login} :{self.content}'


class ChannelMessage(BaseMessage):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            channel: Channel,
            author: ChannelUser
    ) -> None:
        super().__init__(irc_msg, author)
        # variable tags
        self.author: ChannelUser
        self.channel: Channel = channel
        self.bits: int = int(irc_msg.get('bits', 0))
        self.msg_id: Optional[str] = irc_msg.msg_id
        self.custom_reward_id: Optional[str] = irc_msg.get('custom-reward-id')
        self._irc_msg: TwitchIRCMsg = irc_msg

    async def delete(self):
        await self.channel.send_message(f'/delete {self.id}')

    @cached_property
    def parent_message(self) -> Optional[ParentMessage]:
        return self._crate_parent_message(self._irc_msg)

    @property
    def is_reply(self):
        return 'reply-parent-msg-id' in self._irc_msg

    def _crate_parent_message(
            self,
            irc_msg: TwitchIRCMsg
    ) -> Optional[ParentMessage]:
        if 'reply-parent-msg-id' in irc_msg:
            # TODO: Could be better than take private field... but how?
            author = ParentMessageUser(irc_msg.copy(), self.author._irc_conn)
            return ParentMessage(irc_msg.copy(), self.channel, author)
        else:
            return None

    def __str__(self):
        return f'@{self.author.login} to #{self.channel.login} :{self.content}'


class Whisper(BaseMessage):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: GlobalUser
    ):
        irc_msg['id'] = irc_msg.get('message-id')  # rename the field
        super().__init__(irc_msg, author)
        self.thread_id = irc_msg.get('thread-id')

    @property  # may be cached but must not be used more than once.
    def emote_only(self) -> bool:
        return is_emote_only(self.content, self.emotes)

    @emote_only.setter
    def emote_only(self, item):
        pass

    def __str__(self):
        return f'Whisper form @{self.author.login} :{self.content}'
