import asyncio
import websockets

host = 'wss://irc-ws.chat.twitch.tv'
port = '443'
uri = host + port


class Client:

    def __init__(self):
        pass

    async def run(self, token, name, channels) -> None:
        async with websockets.connect(uri) as ws:
            ws.send(f'PASS {token}')
            ws.send(f'NICK {name}')
            for channel in self.channels:
                ws.send(f'JOIN #{channel}')
            self.send_privmsg(channel, 'Hey there!')

            await ws.send(name)
            print(f"> {name}")

            greeting = await ws.recv()
            print(f"< {greeting}")

# asyncio.get_event_loop().run_until_complete(hello())