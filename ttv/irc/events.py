from dataclasses import dataclass

__all__ = ('ClearChatFromUser',)


@dataclass
class ClearChatFromUser:
    target_user_login: str
    target_user_id: str
    target_message_id: str
    ban_duration: int
