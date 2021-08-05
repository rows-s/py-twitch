from dataclasses import dataclass

from .channel import Channel

__all__ = ('OnClearChatFromUser', 'OnChannelJoinError', 'OnNotice', 'OnMessageDelete', 'OnMessageSendError')


@dataclass
class OnClearChatFromUser:
    target_user_login: str
    target_user_id: str
    target_message_id: str
    ban_duration: int


@dataclass
class OnChannelJoinError:
    channel_login: str
    reason: str
    message: str


@dataclass
class OnNotice:
    channel: Channel
    notice_id: str
    message: str


@dataclass
class OnMessageDelete:
    channel: Channel
    user_login: str
    content: str
    message_id: str
    timestamp: int


@dataclass
class OnMessageSendError:
    channel: Channel
    reason: str
    content: str
