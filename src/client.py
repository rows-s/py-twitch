import asyncio
import websockets

uri = 'ws://irc-ws.chat.twitch.tv:80'

def split(text: str, separator: str, max = 0):
    # get len of separator
    sep_len = len(separator)
    # if len is 0, it must be Exception
    # but better we just return whole string
    if sep_len == 0:
        yield text
        raise StopIteration
    # counter counts times we yielded string
    counter = 0
    # i - just index of letter in str
    i = 0
    # simple condition, for check whole string
    # we need (i+sep_len) in condition
    # for don't get IndexError - Exception 
    #
    # example: if len of text = 5, len of sep = 2,
    # then the last index we'll can check is 4,
    # and in the 28th row we'll get text[4:6],
    # but we haven't 5th index of text, so we'll get Exception
    while i+sep_len < len(text):
        #look for separator in text 
        if text[i:i+sep_len] == separator:
            # after find, yeild all before separator
            yield text[:i]
            counter += 1
            # if counts of times we yielded parts equals max(from args)
            # we need to stop this generator
            if counter == max:
                raise StopIteration
            # if we continue we need to delete previous part and separator from text
            text = text[i+sep_len:]
            # we've deleted previous part, 
            # so we need to continue searching from 0th index 
            i = 0
        # just increase the index
        i += 1
    # if out condition (i+sep_len < len(text)) is not True
    # we'll get here
    else:
        # if text endswith the separator we need th delete it
        if text[-sep_len:] == separator:
            yield text[:-sep_len]
        # else we don't need to delete
        else:
            yield text
    # without comments it look simpler

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

            while True:
                received_msgs = await self.ws.recv()
                for received_msg in split(received_msgs, '\r\n'):
                    await self.handle_message(received_msg)
        
        self.event_loop.run_until_complete(start())



    async def handle_message(self, msg):
        print('>', msg)
        if msg.startswith('PING'):
            await self.send('PONG :tmi.twitch.tv')

# asyncio.get_event_loop().run_until_complete(hello())