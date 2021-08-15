from dataclasses import dataclass

from .channel import Channel

__all__ = (
    'OnUserTimeout', 'OnUserBan', 'OnChannelJoinError', 'OnNotice', 'OnMessageDelete', 'OnSendMessageError'
)


@dataclass
class OnUserTimeout:
    channel: Channel
    user_login: str
    user_id: str
    message_id: str
    duration: int
    timestamp: int


@dataclass
class OnUserBan:
    channel: Channel
    user_login: str
    user_id: str
    message_id: str
    timestamp: int


@dataclass
class OnClearChat:
    channel: Channel
    timestamp: int


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
class OnSendMessageError:
    channel: Channel
    reason: str
    message: str
