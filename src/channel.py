
from typing import List, Tuple, Union, Dict, Optional
from websockets.client import connect

from utils import badges_to_dict


class Channel:
    def __init__(self, name: str,
                 mystate_tags: Dict[str, str],
                 ws: connect,
                 tags: Dict[str, str]) -> None:

        self.name: str = name
        self.ws = ws
        self.id: int = int(tags['room-id'])
        self.slow: int = int(tags['slow'])
        self.rituals = int(tags['rituals'])
        self.emote_only:  bool = True if tags['emote-only'] == '1' else False
        self.unique_only: bool = True if tags['r9k'] == '1' else False 
        self.subs_only:   bool = True if tags['subs-only'] == '1' else False
        self.mystate: Channel.LocalState = self.LocalState(mystate_tags)
        self.nameslist: List[str] = []

        value = int(tags['followers-only'])
        self.followers_only = bool(value+1)
        self.followers_only_min = value if value >= 0 else None

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

    def get(self, key: str) -> Union[bool, int, Tuple[bool, Optional[int]]]:
        """
        Return value by key
        params: 'key' - 'key' form tags
        return:
        bool for 'emote-only', 'r9k'(unique-only), 'subs-only'
        int  for 'slow', 'rituals'
        tuple[bool, Optional[int]] for 'followers-only'
        """
        if key == 'emote-only':
            return self.emote_only
        elif key == 'followers-only':
            return self.followers_only, self.followers_only_min
        elif key == 'r9k':
            return self.unique_only
        elif key == 'slow':
            return self.slow
        elif key == 'subs-only':
            return self.subs_only
        elif key == 'rituals':
            return self.rituals

    class LocalState:
        def __init__(self, tags: Dict[str, str]) -> None:
            self.badges: Dict[str, str] = badges_to_dict(tags['badges'])
            self.badges_info: Dict[str, str] = badges_to_dict(tags['badge-info'])
            self.bits: int = int(self.badges['bits']) if 'bits' in self.badges else 0
            self.subscriber: int = int(self.badges['subscriber']) if 'subscriber' in self.badges else 0
            self.admin: bool = True if 'admin' in self.badges else False
            self.broadcaster: bool = True if 'broadcaster' in self.badges else False
            self.mod: bool = True if 'moderator' in self.badges else False
