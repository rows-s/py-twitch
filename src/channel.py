
import websockets

class Channel:
    def __init__(self, name: str, ws: websockets.client.connect, tags: dict):
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


    def update(self, tags: dict):
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

            
    async def send(self, msg: str):
        command = f'PRIVMSG #{self.name} :{msg}'
        print('<', command)
        await self.ws.send(command + '\r\n')
        
    async def disconnect(self):
        command = f'PRIVMSG #{self.name} :/disconnect'
        print('<', command)
        await self.ws.send(command + '\r\n')

    async def clear(self):
        command = f'PRIVMSG #{self.name} :/clear'
        print('<', command)
        await self.ws.send(command + '\r\n')