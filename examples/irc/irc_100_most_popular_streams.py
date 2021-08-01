import asyncio
import os

from ttv.irc import Client, Channel, ChannelMessage
from ttv.api import Api

PASS = os.environ['TTV_IRC_TOKEN']
USERNAME = os.environ['TTV_IRC_NICK']
CHANNEL_COUNT = int(os.getenv('TTV_IRC_CHANNEL_COUNT', 50))
API_TOKEN = os.environ['TTV_API_TOKEN']


class IRCClient(Client):
    async def on_ready(self):
        print(f'Successfully logged in as @{self.login} ({self.global_state.id})')

    async def on_channel_join(self, channel: Channel):
        print(f'Has join #{channel.login}')

    async def on_message(self, message: ChannelMessage):
        print(f'@{message.author.login} in #{message.channel.login}: {message.content}')
        if message.author.login == self.login:
            if message.content == '!stop':
                await self.stop()


async def main():
    ttv_api = await Api.create(API_TOKEN)
    channel = [stream['user_login'] async for stream in ttv_api.get_streams(CHANNEL_COUNT - 1)]
    await ttv_api.close()
    channel.append(USERNAME)
    await IRCClient(PASS, USERNAME).start(channel)

asyncio.get_event_loop().run_until_complete(main())
