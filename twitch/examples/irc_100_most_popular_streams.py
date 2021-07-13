try:
    import twitch
except ImportError:
    import sys
    sys.path.append('../../..')
import asyncio

import config
from twitch.irc.client import Client
from twitch.irc.messages import ChannelMessage
from twitch.irc.channel import Channel
from twitch.api.client import Api
from twitch.api.exceptions import InvalidToken

ttv_chat_bot = Client(config.token, config.nick)


@ttv_chat_bot.event
async def on_self_join(channel: Channel):
    print(f'Has join #{channel.login}')


@ttv_chat_bot.event
async def on_reconnect():
    print('\n\n\nRECONNECTED\n\n\n')


@ttv_chat_bot.event
async def on_message(message: ChannelMessage):
    print(f'@{message.author.login} in #{message.channel.login}: {message.content}')


async def main(config_file_name: str = 'config.py'):
    try:
        ttv_api = await Api.create(config.app_token)
    except InvalidToken:
        raw_new_app_token = await Api.create_app_token(config.client_id, config.secret, config.scope)
        new_app_token = raw_new_app_token['access_token']
        with open(config_file_name, 'r+') as config_file:
            config_text = config_file.read()
            config_text.replace(config.app_token, new_app_token)
            config_file.truncate(0)
            config_file.write(config_text)
        print('# Created new app token')
        ttv_api = await Api.create(new_app_token)

    streams = [stream['user_login'] async for stream in ttv_api.get_streams(100)]
    streams.append(config.nick)
    asyncio.get_event_loop().create_task(ttv_chat_bot.start(streams))

asyncio.get_event_loop().create_task(main())
asyncio.get_event_loop().run_forever()
