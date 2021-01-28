import asyncio
import re
from random import choice

from irc_client import Client
from config import token, nick, app_token2
from api import Api
from time import time

from irc_channel import Channel

bot = Client(token, nick)
counter = 0
room_update_counter = 0


@bot.event
async def on_channel_update(before, after):
    global counter, room_update_counter
    counter += 1
    room_update_counter += 1
    print(f'ROOMSTATE in #{before.name}')


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
async def on_self_join(channel):
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
async def on_message_delete(channel, user_name, text, message_id):
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
    if str(message.author.id) == bot.global_state.id:
        if message.content == '!stop':
            print(f'!!!!handled {counter} various events after {time()-start_time} seconds')
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
            await message.channel.send(f'{counter} after {time()-start_time}')
        elif message.content == '!delays':
            content = ''
            for channel_name in bot._delayed_irc_parts:
                content = channel_name + '\n'
                for parts in bot._delayed_irc_parts[channel_name]:
                    command = parts[1]
                    content += '>>>>' + command[1] + '\n'
            else:
                if len(bot._delayed_irc_parts) == 0:
                    content = 'Just 0'
            await message.channel.send(content)
        elif message.content == '!disconnect':
            channels = list(bot._channels_by_name.values())
            channel = choice(channels)
            await message.channel.send(f'have chosen {channel.name}')
            await channel.disconnect()


# with open(r"D:\Users\I3rowser\Desktop\to distribute\py-twitch\src\TMP.txt", encoding="utf8") as file:
#     text = file.read()
#     regul = r'<a[^>]*tw-full-width tw-link tw-link--hover-underline-none ' \
#             r'tw-link--inherit[^>]*href="https://www.twitch.tv/([^"]*)[^>]*>'
#     result = re.findall(regul, text)
#
# print(f'!\nWe are joining {len(result)} of channels as bot')

# result.insert(0, 'rows_s')
# bot.run(channels=result[:100])
async def begin():
    do = input('processing type: ')
    if do.lower() == 'global':
        api = await Api.create(app_token2)
        ids = []
        async for stream in api.get_streams(99):
            ids.append(stream['user_id'])
        logins = []
        async for user in api.get_users(99, user_id=ids):
            logins.append(user['login'])
        logins.append('rows_s')
        del api
        await Api.close()
    else:
        logins = ['rows_s', 'pitsxs']
    asyncio.get_event_loop().create_task(bot.start(logins))
start_time = time()
# bot.run(channels=['rows_s', 'pitsxs'])
asyncio.get_event_loop().create_task(begin())
asyncio.get_event_loop().run_forever()
