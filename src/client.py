import asyncio
import websockets

uri = 'ws://irc-ws.chat.twitch.tv:80'


class Client: 
    def __init__(self, token, nick, channels):
        self.token = token
        self.nick = nick
        self.channels = channels
        self.ws = None
        self.event_loop = asyncio.get_event_loop()
        
    async def send(self, command):
        await self.ws.send(command + '\r\n')
        if not command.startswith('PASS'):
            print('<', command)

    async def send_msg(self, channel, text):
        await self.send(f'PRIVMSG #{channel} :{text}')

    def run(self):
        async def start():
            self.ws = await websockets.connect(uri)
            await self.send(f'PASS {self.token}')
            await self.send(f'NICK {self.nick}')
            for channel in self.channels:
                await self.send(f'JOIN #{channel}')
                await self.send_msg(channel, 'Ooh, Hi!')
                await self.send_msg(channel, 'Try to ban:')
                await self.send_msg(channel, '/ban ninja without reason')

            while True:
                received_msgs = await self.ws.recv()
                for received_msg in received_msgs.split('\r\n'):
                    await self.handle_message(received_msg)
        
        self.event_loop.run_until_complete(start())

    async def handle_message(self, msg):
        print('>', msg)
        if len(msg) == 0:
            return
        if msg.startswith('PING'):
            await self.send('PONG :tmi.twitch.tv')
    
    async def parse_message(self, msg):
        parts = [part for part in msg.split(':', 2)]
        if len(parts) == 3:
            message = parts[2]
        if len(parts) > 1:
            command = parts[1]
        prefix = parts[0]