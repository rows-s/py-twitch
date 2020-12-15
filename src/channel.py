
from typing import Optional, Dict
import websockets

class Channel:
    def __init__(self, name: str, ws: websockets.client.connect, tags: Dict[str, str]) -> None: 
        self.name: str = name
        self.ws: websockets.client.Connect = ws
        self.id: int = None
        self.emote_only: bool = False
        self.followers_only: bool = False
        self.followers_only_min: int = None
        self.unique_only: bool = False
        self.slow: int = 0
        self.subs_only: bool = None
        self.nameslist: Optional[list] = None

        for key in tags.keys():
            if key == 'room-id':
                self.id = int(tags[key])

            elif key == 'emote-only':
                self.emote_only = True if tags[key] == '1' else False

            elif key == 'followers-only':
                value = int(tags[key])
                self.followers_only = bool(value+1)
                if value > 0:
                    self.followers_only_min = value
                else:
                    self.followers_only_min = 0

            elif key == 'r9k':
                self.unique_only = True if tags[key] == '1' else False

            elif key == 'slow':
                self.slow = int(tags[key])

            elif key == 'subs-only':
                self.subs_only = True if tags[key] == '1' else False


    def update(self, tags: Dict[str, str]) -> None:
        for key in tags.keys():
            if key == 'emote-only':
                self.emote_only = True if tags[key] == '1' else False

            elif key == 'followers-only':
                value = int(tags[key])
                self.followers_only = bool(value+1)
                if value > 0:
                    self.followers_only_min = value
                else:
                    self.followers_only_min = 0

            elif key == 'r9k':
                self.unique_only = True if tags[key] == '1' else False

            elif key == 'slow':
                self.slow = int(tags[key])

            elif key == 'subs-only':
                self.subs_only = True if tags[key] == '1' else False

            
    async def send(self, msg: str) -> str:
        command = f'PRIVMSG #{self.name} :{msg}'
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