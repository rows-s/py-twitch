import irc_client
import config
from api import Api

from errors import HTTPError

bot = irc_client.Client(config.token, config.nick)
# api = Api()


@bot.event
async def on_login():
    print(f'We have started! With\n'
          f'Name = {bot.global_state.display_name}\n'
          f'Color = {bot.global_state.color}\n'
          f'Id = {bot.global_state.id}\n'
          f'Badges = {bot.global_state.badges}\n'
          f'Emote = {bot.global_state.emote_sets}')


@bot.event
async def on_self_join(channel):
    print(f'We have joined #{channel.name}')


async def to_do():
    api = await Api.create(config.app_token)
    print('Start commercial:\n    ', end='')
    try:
        print(await api.start_commercial(broadcaster_id=192827780, length=60))
    except HTTPError as e:
        print(e)
    print('get_extension_analytics:\n    ', end='')
    try:
        print(await api.get_extension_analytics(1).__anext__())
    except HTTPError as e:
        print(e)

    print('get_game_analytics:\n    ', end='')
    try:
        print(await api.get_game_analytics(1).__anext__())
    except HTTPError as e:
        print(e)

    print('get_bits_leaderboard:\n    ', end='')
    try:
        print(await api.get_bits_leaderboard(1).__anext__())
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('get_bits_leaderboard has got 0 data')

    print('get_cheermotes:\n    ', end='')
    try:
        print(await api.get_cheermotes(1).__anext__())
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('get_cheermotes has got 0 data')

    print('get_extension_transactions:\n    ', end='')
    try:
        print(await api.get_extension_transactions(1, extension_id=192827780, transaction_id=192827780).__anext__())
    except TypeError as e:
        print(e)
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('get_extension_transactions has got 0 data')

    print('create_custom_rewards:\n    ', end='')
    try:
        print(await api.create_custom_rewards(**{'title': 'Test', 'cost': 50000}, broadcaster_id=192827780))
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('create_custom_rewards has got 0 data')

    print('delete_custom_reward:\n    ', end='')
    try:
        print(await api.delete_custom_reward(broadcaster_id=192827780, reward_id=192827780))
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('delete_custom_reward has got 0 data')

    print('get_custom_reward:\n    ', end='')
    try:
        print(await api.get_custom_reward(1, broadcaster_id=192827780).__anext__())
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('get_custom_reward has got 0 data')

    print('get_custom_reward_redemption:\n    ', end='')
    try:
        print(await api.get_custom_reward_redemption(1, broadcaster_id=192827780, reward_id='123').__anext__())
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('get_custom_reward_redemption has got 0 data')

    print('update_custom_reward:\n    ', end='')
    try:
        print(await api.update_custom_reward(broadcaster_id=192827780, reward_id='123'))
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('update_custom_reward has got 0 data')

    print('replace_stream_tags:\n    ', end='')
    try:
        print(await api.replace_stream_tags(broadcaster_id=192827780))
    except HTTPError as e:
        print(e)
    except StopAsyncIteration:
        print('replace_stream_tags has got 0 data')
    await api.close()


async def to_do2():
    api = await Api.create(config.app_token)
    params = {'language': 'ru'}
    async for stream in api.get_streams(100, **params):
        print(stream)
    generator = api.get_streams(1, **params)
    print('Try once:\n    ', await api.once(generator))
    await api.close()

bot.loop.run_until_complete(to_do())


