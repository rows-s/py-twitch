
from typing import List, Tuple, Union, Dict, Optional
from websockets import WebSocketClientProtocol

from utils import parse_raw_badges


class Channel:
    def __init__(
        self, 
        name: str,
        ws: WebSocketClientProtocol,
        tags: Dict[str, str]
    ) -> None:
        self.name: str = name
        self.ws: WebSocketClientProtocol = ws
        self.id: str = tags['room-id']
        self.slow: int = int(tags['slow'])
        self.rituals = int(tags['rituals'])
        self.emote_only:  bool = True if tags['emote-only'] == '1' else False
        self.unique_only: bool = True if tags['r9k'] == '1' else False 
        self.subs_only:   bool = True if tags['subs-only'] == '1' else False
        self.my_state: Optional[LocalState] = None
        self.nameslist: Union[Tuple[str], List[str]] = []
        # follower only state
        followers_only_value = int(tags['followers-only'])
        self.followers_only = bool(followers_only_value+1)  # -1 - is off, otherwise - is on
        self.followers_only_min = followers_only_value if followers_only_value >= 0 else None

    async def send(self, conntent: str) -> str:
        command = f'PRIVMSG #{self.name} :{conntent}'
        await self.ws.send(command + '\r\n')
        return command

    async def disconnect(self) -> str:
        command = f'PRIVMSG #{self.name} :/disconnect'
        await self.ws.send(command + '\r\n')
        return command

    async def clear(self) -> str:
        command = f'PRIVMSG #{self.name} :/clear'
        await self.ws.send(command + '\r\n')
        return command

    def update(self, key: str, value: str) -> None:
        if key == 'emote-only':
            self.emote_only = True if value == '1' else False

        elif key == 'followers-only':
            value = int(value)
            self.followers_only = bool(value+1)
            if value > 0:
                self.followers_only_min = value
            else:
                self.followers_only_min = None

        elif key == 'r9k':
            self.unique_only = True if value == '1' else False

        elif key == 'slow':
            self.slow = int(value)

        elif key == 'subs-only':
            self.subs_only = True if value == '1' else False


class LocalState:
    def __init__(self, tags: Dict[str, str]) -> None:
        self.badges: Dict[str, str] = parse_raw_badges(tags['badges'])
        self.badges_info: Dict[str, str] = parse_raw_badges(tags['badge-info'])
        self.bits: int = int(self.badges['bits']) if 'bits' in self.badges else 0
        self.subscriber: int = int(self.badges['subscriber']) if 'subscriber' in self.badges else 0
        self.admin: bool = True if 'admin' in self.badges else False
        self.broadcaster: bool = True if 'broadcaster' in self.badges else False
        self.mod: bool = True if 'moderator' in self.badges else False
