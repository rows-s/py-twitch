
from utils import parse_raw_badges, parse_raw_emotes

from typing import Dict, Callable


__all__ = (
    'Message'
)


class Whisper:
    def __init__(
            self,
            tags: Dict[str, str],
            content: str,
            send_whisper: Callable
    ):
        # recipient
        self.recipient_id = tags.get('user-id')
        self.recipient_login = tags.get('user-login')
        self.recipient_display_name = tags.get('display-name')
        self.recipient_color = tags.get('color')
        self.recipient_badges = parse_raw_badges(tags.get('badges', ''))
        # whisper
        self.id = tags.get('message-id')
        self.thread_id = tags.get('thread-id')
        self.emotes = parse_raw_emotes(tags.get('emotes', ''))
        self.content = content
        # callback
        self._send_whisper: Callable = send_whisper

    async def answer(
            self,
            content: str,
            *,
            via_channel: str = None
    ) -> None:
        await self._send_whisper(self.recipient_login, content, whisper_channel_login=via_channel)
