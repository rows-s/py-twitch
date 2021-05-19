import asyncio

from time import time

from irc_messages import ChannelMessage, WhisperMessage
from irc_client import Client
from irc_channel import Channel
from api import Api
from config import token, nick, app_token
app_token = app_token

bot = Client(token, nick)
counter = 0
start_time = time()

all_events = list(Client.events_handler_names) + list(Client.user_event_handler_names)


@bot.events(*all_events)
async def handle_everything(*args):
    global counter
    counter += 1
    if counter == 5000000:
        print(f'{counter} after {time()-start_time}')
        input('Hello!')
        quit()


@bot.event
async def on_message(message: ChannelMessage):
    await handle_everything()
    if message.author.id == bot.global_state.id:  # if message from bot owner
        if message.content == '!state':  # if text of message == '!state'
            print(f'{counter} after {time()-start_time}')
            await message.channel.send_message(f'{counter} after {time() - start_time}')
        if message.content == '!rejoin':
            await bot.join_channel(login=next(iter(bot.joined_channels_logins)))
            await message.channel.send_message(
                f'rejoin request to #{next(iter(bot.joined_channels_logins))} has been sent'
            )
        if message.content == '!left':
            login = next(iter(bot.joined_channels_logins))
            bot._channels_by_login.pop(login, None)


@bot.event
async def on_whisper(wisper: WhisperMessage):
    await handle_everything()
    await wisper.send_whisper(wisper.content)


@bot.event
async def on_login():
    await handle_everything()
    print(bot.global_state.id)


@bot.event
async def on_join(channel: Channel, user_login):
    await handle_everything()
    if user_login == bot.global_state.login:
        print(f'user @{user_login} has joined #{channel.login}')


@bot.event
async def on_self_join(channel):
    await handle_everything()
    # print(f'have joined #{channel.login} as @{bot.global_state.login}')\


@bot.event
async def on_channel_update(before: Channel, after: Channel):
    await handle_everything()
    print(f'#{before.login} has been updated')


@bot.events('on_my_state_update', 'on_nameslist_update')
async def channel_update(channel: Channel, before, after):
    await handle_everything()
    print(f'#{channel.login} has got new', 'local_state' if type(before) != tuple else 'nameslist')


async def start():
    api = await Api.create(app_token)
    logins = [stream['user_login'] async for stream in api.get_streams(101)]
    logins.insert(0, 'rows_s')
    # start
    bot.loop.create_task(bot.start(logins))
    while True:
        # every 30 minutes
        await asyncio.sleep(30 * 60)
        # left all channels
        bot.loop.create_task(bot.part_channels(bot.joined_channels_logins.copy()))
        # get 99+1 top channels
        new_logins = [stream['user_login'] async for stream in api.get_streams(99)]
        new_logins.insert(0, 'rows_s')
        # join channels
        await bot.join_channels(new_logins)
        print('UPDATED CHANNELS\n\n\n')
    # await bot.start(['rows_s', 'pitsxs'])

asyncio.get_event_loop().run_until_complete(start())
