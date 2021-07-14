from dataclasses import dataclass

__all__ = ('ClearChatFromUser',)


@dataclass
class ClearChatFromUser:
    target_user_login: str
    taget_user_id: str
    taget_message_id: str
    ban_duration: int
