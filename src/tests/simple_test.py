import asyncio

from time import time
from irc_message import Message
from irc_client import Client
from api import Api
from config import token, nick, app_token2


bot = Client(token, nick)
counter = 0
start_time = time()

on_events = list(bot.events_names) + list(bot.user_events_names)


@bot.events(on_events)
async def handle_everything(*args):
    global counter
    counter += 1

# bot.events(handle_everything, list(bot.events_names) + list(bot.user_events_names))


@bot.event
async def on_message(message: Message):
    if str(message.author.id) == bot.global_state.id:  # if message from bot owner
        if str(message.channel.id) == bot.global_state.id:  # if message in chat of bot owner
            if message.content == '!state':  # if text of message == '!state'
                print(f'{counter} after {time()-start_time}')
                await message.channel.send(f'{counter} after {time()-start_time}')


async def start():
    api = await Api.create(app_token2)
    ids = [stream['user_id'] async for stream in api.get_streams(99)]
    logins = [user['login'] async for user in api.get_users(99, user_id=ids)]
    logins.insert(0, 'rows_s')
    del api
    await Api.close()
    asyncio.get_event_loop().create_task(bot.start(channels=logins))

asyncio.get_event_loop().create_task(start())
asyncio.get_event_loop().run_forever()
