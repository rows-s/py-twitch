import asyncio
import websockets

host = 'wss://irc-ws.chat.twitch.tv'
port = '443'
uri = host + port
class Client:

    def __init__(self, token):
        pass

    async def run(self):
        async with websockets.connect(uri) as ws:
            name = input("What's your name? ")

            await ws.send(name)
            print(f"> {name}")

            greeting = await ws.recv()
            print(f"< {greeting}")

# asyncio.get_event_loop().run_until_complete(hello())