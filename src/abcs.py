from abc import ABC

from irc_channel import Channel
from irc_member import Member
from utils import parse_raw_emotes

from typing import Dict, List, Tuple


class AbstractMessage(ABC):
    def __init__(
            self,
            channel: Channel,
            author: Member,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        # prepared
        self.channel: Channel = channel
        self.author: Member = author
        self.content: str = content
        # stable tags
        self.id: str = tags.get('id')
        self.time: int = int(tags.get('tmi-sent-ts', '0'))
        self.flags: str = tags.get('flags')
        # emotes
        self.emote_only: bool = tags.get('emote-only') == '1'
        self.emotes: Dict[str, List[Tuple[int, int]]] = parse_raw_emotes(tags.get('emotes', ''))
