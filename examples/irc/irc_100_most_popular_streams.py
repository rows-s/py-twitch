import asyncio
import os

from ttv.irc import Client, Channel, ChannelMessage
from ttv.api import Api

irc_token = os.getenv('TTV_IRC_TOKEN')
irc_nick = os.getenv('TTV_IRC_NICK')
channel_count = int(os.getenv('TTV_IRC_CHANNEL_COUNT'))
api_token = os.getenv('TTV_API_TOKEN')
ttv_chat_bot = Client(irc_token, irc_nick)


@ttv_chat_bot.event
async def on_login():
    print('Successfully logged in')


@ttv_chat_bot.event
async def on_channel_join(channel: Channel):
    print(f'Has join #{channel.login}')


@ttv_chat_bot.event
async def on_message(message: ChannelMessage):
    print(f'@{message.author.login} in #{message.channel.login}: {message.content}')


async def main():
    ttv_api = await Api.create(api_token)
    streams = [stream['user_login'] async for stream in ttv_api.get_streams(channel_count - 1)]
    streams.append(irc_nick)
    await ttv_chat_bot.start(streams)

asyncio.get_event_loop().run_until_complete(main())
