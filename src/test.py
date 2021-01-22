import asyncio
import re

import client
import config
<<<<<<< Updated upstream:src/test.py
from time import time

bot = client.Client(config.token, config.nick)
=======
from api import Api
from time import time

from irc_channel import Channel

bot = irc_client.Client(config.token, config.nick)
>>>>>>> Stashed changes:src/tests/test_chat_bot.py
counter = 0


room_update_counter = 0

@bot.event
<<<<<<< Updated upstream:src/test.py
async def on_room_update(channel, key, before, after):
    global counter, room_update_counter
    counter += 1
    room_update_counter += 1
    print(f'ROOMSTATE in #{channel.name} with {key} set {after} after {before}')
=======
async def on_room_update(channel, before: Channel, after: Channel):
    global counter, room_update_counter
    counter += 1
    room_update_counter += 1
    print(f'ROOMSTATE in #{channel.name}')
    before_attrs = before.__dir__()
    after_attrs = after.__dir__()
    for before_attr, after_attr in zip(before_attrs, after_attrs):
        before_value = getattr(before, before_attr)
        after_value = getattr(after, after_attr)
        if before_value != after_value:
            print(f'>>>> {before_attr}/{after_attr} get new value {before_value} after {after_value}')
            break
>>>>>>> Stashed changes:src/tests/test_chat_bot.py


@bot.event
async def on_login():
    print(f'We have started! With\n'
          f'Name = {bot.global_state.name}\n'
          f'Color = {bot.global_state.color}\n'
          f'Id = {bot.global_state.id}\n'
          f'Badges = {bot.global_state.badges}\n'
          f'Emote = {bot.global_state.emotes}')


room_join_counter = 0
@bot.event
async def on_room_join(channel):
    global counter, room_join_counter
    counter += 1
    room_join_counter += 1
    print(f'#{channel.name} has been joined ROOMSTATE')


join_counter = 0
@bot.event
async def on_join(channel, name):
    global counter, join_counter
    counter += 1
    join_counter += 1


left_counter = 0
@bot.event
async def on_left(channel, name):
    global counter, left_counter
    counter += 1
    left_counter += 1


clear_user_counter = 0
@bot.event
async def on_clear_user(channel, user_name, ban_duration):
    global counter, clear_user_counter
    counter += 1
    clear_user_counter += 1
    print(f'CLEARCHAT #{channel.name} has been cleared from @{user_name} after {ban_duration} seconds ban')


clear_chat_counter = 0
@bot.event
async def on_clear_chat(channel):
    global counter, clear_chat_counter
    counter += 1
    clear_chat_counter += 1
    print(f'CLEARCHAT #{channel.name} has been cleared')


clear_message_counter = 0
@bot.event
async def on_clear_message(channel, user_name, text, message_id):
    global counter, clear_message_counter
    counter += 1
    clear_message_counter += 1
    channel = channel.name
    print(f'CLEARMSG Message "{text}" by @{user_name} has been deleted',
          f'in #{channel} with id="{message_id}"')


host_couter = 0
@bot.event
async def on_start_host(channel, viewers, hosted):
    global counter, host_couter
    counter += 1
    host_couter += 1
    channel = channel.name
    print(f'#{channel} got start HOSTTARGET with {viewers} by @{hosted}')


unhost_counter = 0
@bot.event
async def on_stop_host(channel, viewers):
    global counter, unhost_counter
    counter += 1
    unhost_counter += 1
    channel = channel.name
    print(f'#{channel} got stop HOSTTARGET with {viewers} of viewers')


notice_counter = 0
@bot.event
async def on_notice(channel, notice_id, notice_message):
    global counter, notice_counter
    counter += 1
    notice_counter += 1
    channel = channel.name
    print(f'#{channel} got NOTICE with id="{notice_id}" and message="{notice_message}"')


user_event_counter = 0
@bot.event
async def on_user_event(event):
    global counter, user_event_counter
    counter += 1
    user_event_counter += 1
    print(f'USERNOTICE {type(event).__name__} by {event.author.name} in #{event.channel.name}, '
          f'sever said - "{event.system_msg}"')


message_counter = 0
@bot.event
async def on_message(message):
    global counter, start_time, message_counter, room_update_counter, room_join_counter, join_counter
    global left_counter, clear_user_counter, clear_chat_counter, clear_message_counter, host_couter
    global unhost_counter, notice_counter, user_event_counter
    counter += 1
    message_counter += 1
    if message.author.id == bot.global_state.id:
        if message.content == '!stop':
            print(f'!!!!Stoped!!!! handled {counter} various events after {time()-start_time} seconds')
            print(f'messages - {message_counter}')
            print(f'room updates - {room_update_counter}')
            print(f'room joins - {room_join_counter}')
            print(f'joins - {join_counter}')
            print(f'lefts - {left_counter}')
            print(f'clear users - {clear_user_counter}')
            print(f'clear chats - {clear_chat_counter}')
            print(f'clear messsages - {clear_message_counter}')
            print(f'hosts - {host_couter}')
            print(f'unhosts - {unhost_counter}')
            print(f'notices - {notice_counter}')
            print(f'user events - {user_event_counter}')

start_time = time()

<<<<<<< Updated upstream:src/test.py
with open('TMP.txt', encoding="utf8") as file:
    text = file.read()
    regul = r'<a[^>]*tw-full-width tw-link tw-link--hover-underline-none ' \
            r'tw-link--inherit[^>]*href="https://www.twitch.tv/([^"]*)[^>]*>'
    result = re.findall(regul, text)

print('!\nWe are joining {} of channels as bot'.format(len(result)))
start_time = time()
result.insert(0, 'rows_s')
bot.run(channels=result[:100])
=======

async def start():
    api = await Api.create(config.app_token2)
    channels_ids = []
    channels_logins = []
    async for channel in api.get_streams(99):
        channels_ids.append(channel['user_id'])
    async for user in api.get_users(99, user_id=channels_ids):
        channels_logins.append(user['login'])
    del api
    await Api.close()
    channels_logins.append('rows_s')
    asyncio.get_event_loop().create_task(
        bot.start(channels=channels_logins, ws_params=config.ws_params)
    )
    print(f'!\nWe are joining {len(channels_logins)} of channels as bot')


asyncio.get_event_loop().create_task(start())
asyncio.get_event_loop().run_forever()
>>>>>>> Stashed changes:src/tests/test_chat_bot.py
