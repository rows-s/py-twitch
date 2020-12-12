import asyncio
import websockets
import Message
from utils import is_int
# our uri to connent to sever
uri = 'wss://irc-ws.chat.twitch.tv:443'

# class Client, it will create bots
class Client: 
    def __init__(self, token: str, login: str, channels: iter):
        self.token = token
        self.login = login
        self.channels = channels
        self.ws = None
        self.event_loop = asyncio.get_event_loop()
        self.nick = None
        self.color = None
        self.id = None
        self.emotes = None


    async def send(self, command: str) -> None:
        await self.ws.send(command + '\r\n')
        if not command.startswith('PASS'):
            print('<', command)


    async def send_msg(self, channel: str, text: str) -> None:
        await self.send(f'PRIVMSG #{channel} :{text}')


    def run(self):
        async def start():
            self.ws = await websockets.client.connect(uri)
            await self.send('CAP REQ :twitch.tv/commands')
            await self.send('CAP REQ :twitch.tv/membership')
            await self.send('CAP REQ :twitch.tv/tags')
            await self.send(f'PASS {self.token}')
            await self.send(f'NICK {self.login}')
            for channel in self.channels:
                await self.send(f'JOIN #{channel}')
                #await self.send_msg(channel, 'Ooh, Hi!')
            self.channels = {}
            #await self.send(f'PRIVMSG 524306485 :test')

            while True:
                received_msgs = await self.ws.recv()
                for received_msg in received_msgs.split('\r\n'):
                    self.event_loop.create_task(self.handle_message(received_msg))
        
        self.event_loop.run_until_complete(start())


    async def handle_message(self, msg):
        print('>', msg)
        if len(msg) == 0:
            return
        if msg.startswith('PING'):
            await self.send('PONG :tmi.twitch.tv')
            return
        tags, command, message = await self.parse_message(msg)
        print(f'    tags = {tags}\n    command = {command}\n    message = {message}')
        if is_int(command[1]):
            return
        elif command[1] == 'GLOBALUSERSTATE':
            self.color = tags['color']
            self.nick = tags['display-name']
            self.emotes = tags['emote-sets'].split(',')
            self.emotes = tuple(map(int, self.emotes))
            self.id = int(tags['user-id'])
        elif command[1] == 'ROOMSTATE':
            pass
        elif command[1] == 'USERSTATE':
            pass
        elif command[1] == 'JOIN':
            pass
        elif command[1] == 'JOIN':
            pass
        print('!!!Found nothing!!!')
        

    async def parse_message(self, msg):
        message = None
        tags = None
        command = None

        parts = msg.split(':', 2)
        tags = await self.prefix_to_dict(parts[0])
        command = parts[1].split( )
        if len(parts) == 3:
            message = parts[2]

        return tags, command, message


    async def prefix_to_dict(self, prefix):
        tags = {}
        i = 0
        last = 0
        while i < len(prefix):
            if prefix[i] == '=':
                key = prefix[last:i]
                j = i + 1
                while j < len(prefix):
                    if prefix[j] == ';':
                        value = prefix[i+1:j]
                        tags[key] = value
                        i = last = j + 1
                        break
                    j += 1
                else:
                    value = prefix[i+1:-1]
                    tags[key] = value
            i += 1
        return tags
                        