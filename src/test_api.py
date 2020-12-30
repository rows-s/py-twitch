from time import time

import client
import config
from api import Api
import asyncio
import re

from errors import HTTPError

bot = client.Client(config.token, config.nick)
api = Api()

@bot.event
async def on_login():
    print(f'We have started! With\n'
          f'Name = {bot.global_state.name}\n'
          f'Color = {bot.global_state.color}\n'
          f'Id = {bot.global_state.id}\n'
          f'Badges = {bot.global_state.badges}\n'
          f'Emote = {bot.global_state.emotes}')


@bot.event
async def on_room_join(channel):
    print(f'We have joined #{channel.name}')


async def to_do():
    await api.set_auth(config.auth)
    # print('Multiple requests(loop):')
    # async for game in api.get_top_games(21):
    #     print('    ', game)
    # print('Single request:\n    ', end='')
    # print(await api.get_top_games(1).__anext__())
    #
    # print('Start commercial:\n    ', end='')
    # try:
    #     print(await api.start_commercial(broadcaster_id=192827780, length=60))
    # except HTTPError as e:
    #     print(e)
    #
    # print('get_extension_analytics:\n    ', end='')
    # try:
    #     print(await api.get_extension_analytics(1).__anext__())
    # except HTTPError as e:
    #     print(e)
    #
    # print('get_game_analytics:\n    ', end='')
    # try:
    #     print(await api.get_extension_analytics(1).__anext__())
    # except HTTPError as e:
    #     print(e)
    #
    # print('get_bits_leaderboard:\n    ', end='')
    # try:
    #     print(await api.get_bits_leaderboard(1).__anext__())
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('get_bits_leaderboard has got 0 data')
    #
    # print('get_cheermotes:\n    ', end='')
    # try:
    #     print(await api.get_cheermotes(1, 192827780).__anext__())
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('get_cheermotes has got 0 data')
    #
    # print('get_extension_transactions:\n    ', end='')
    # try:
    #     print(await api.get_extension_transactions(1, extension_id=192827780, traransaction_id=192827780).__anext__())
    # except TypeError as e:
    #     print(e)
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('get_extension_transactions has got 0 data')
    #
    # print('create_custom_rewards:\n    ', end='')
    # try:
    #     print(await api.create_custom_rewards({'title': 'Test', 'cost': 50000}, broadcaster_id=192827780))
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('create_custom_rewards has got 0 data')
    #
    # print('delete_custom_reward:\n    ', end='')
    # try:
    #     print(await api.delete_custom_reward(broadcaster_id=192827780, reward_id=192827780))
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('delete_custom_reward has got 0 data')
    #
    # print('get_custom_reward:\n    ', end='')
    # try:
    #     print(await api.get_custom_reward(1, broadcaster_id=192827780).__anext__())
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('get_custom_reward has got 0 data')
    #
    # print('get_custom_reward_redemption:\n    ', end='')
    # try:
    #     print(await api.get_custom_reward_redemption(1, broadcaster_id=192827780, reward_id='123').__anext__())
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('get_custom_reward_redemption has got 0 data')
    #
    # print('update_custom_reward:\n    ', end='')
    # try:
    #     print(await api.update_custom_reward(broadcaster_id=192827780, reward_id='123'))
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('update_custom_reward has got 0 data')
    #
    # print('update_redemption_status:\n    ', end='')
    # try:
    #     print(await api.update_redemption_status(broadcaster_id=192827780, reward_id='123', id='123', status='CANCELED'))
    # except HTTPError as e:
    #     print(e)
    # except StopAsyncIteration:
    #     print('update_redemption_status has got 0 data')

    msg_id = ['123', '393']
    msg_text =['Hello World!', 'Boooooo!']
    user_id = [23749, 23422]
    print(await api.check_automod_status(broadcaster_id=192827780, msg_id=msg_id, msg_text=msg_text, user_id=user_id))
    # channels.append(re.findall('/live_user_([^-]*)', stream['thumbnail_url'])[0])

bot.loop.run_until_complete(to_do())


