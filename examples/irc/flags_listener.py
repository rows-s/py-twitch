import asyncio
import os

from ttv.irc import Client, Channel, ChannelMessage, ANON_TOKEN, ANON_LOGIN
from ttv.api import Api

TOKEN = os.getenv('TTV_IRC_TOKEN', ANON_TOKEN)
LOGIN = os.getenv('TTV_IRC_NICK', ANON_LOGIN)
CHANNEL_COUNT = int(os.getenv('TTV_IRC_CHANNEL_COUNT', 10))
API_TOKEN = os.environ['TTV_API_TOKEN']


class IRCClient(Client):
    async def on_ready(self):
        print(f'Successfully logged in as @{self.login} ({self.global_state.id})')

    async def on_channel_join(self, channel: Channel):
        print(f'Listening to #{channel.login}')

    async def on_message(self, message: ChannelMessage):
        if message.author.login == self.login:
            if message.content == '!stop':
                await self.stop()
        elif message.flags:
            print(message)
            for flag in message.flags:
                for sub_flag in flag:
                    print('   ', sub_flag)


async def main():
    api = await Api.create(API_TOKEN)
    channels = [stream['user_login'] async for stream in api.get_streams(CHANNEL_COUNT - 1)] + [LOGIN]
    await api.close()
    await IRCClient(TOKEN, LOGIN).start(channels)

asyncio.run(main())
