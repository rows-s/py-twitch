import asyncio
import websockets

uri = 'ws://irc-ws.chat.twitch.tv:80'

def split(text: str, separator: str, max = 0):
    sep_len = len(separator)
    if sep_len == 0:
        return text
    counter = 0
    i = 0
    while i+sep_len < len(text):
        if text[i:i+sep_len] == separator:
            yield text[:i]
            counter += 1
            if counter == max:
                return None
            text = text[i+sep_len:]
            i = 0
        i += 1
    else:
        if text[-sep_len:] == separator:
            yield text[:-sep_len]
        else:
            yield text

class Client:

    def __init__(self, token, nick, channels):
        self.token = token
        self.nick = nick
        self.channels = channels
        
    async def send(self, ws, command):
        await ws.send(command + '\r\n')
        if not command.startswith('PASS'):
            print('<', command)

    # async def privmsg(self, ws, command):
    #     to_send = 'PRIVMSG' + command
    #     ws.send()

    async def run(self):
        async with websockets.connect(uri) as ws:
            await self.send(ws, f'PASS {self.token}')
            await self.send(ws, f'NICK {self.nick}')
            for channel in self.channels:
                await self.send(ws, f'JOIN #{channel}')

            while True:
                received_msgs = await ws.recv()
                for received_msg in split(received_msgs, '\r\n'):
                    await self.handle_message(received_msg)
    
    # async def run(self):
    #     asyncio.get_event_loop().run_until_complete(self.run_ws())
    #     asyncio.get_event_loop().run_forever()
            
        

    async def handle_message(self, msg):
        print('>', msg)

# asyncio.get_event_loop().run_until_complete(hello())