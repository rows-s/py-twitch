
import websockets

class Channel:
    def __init__(self, name: str, ws: websockets.client.connect, tags: dict) -> None: 
        self.name = name
        self.ws = ws
        self.id = None
        self.emote_only = None
        self.followers_only = None
        self.followers_only_min = None
        self.unique_only = None
        self.slow = None
        self.subs_only = None

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


    def update(self, tags: dict) -> None:
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