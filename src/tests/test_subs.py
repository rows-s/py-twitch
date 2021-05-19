from api import Api
from irc_client import Client as IRCClient
import asyncio

from aiohttp import web

import config
import eventsub
import eventsub_events


nick = config.nick
test_user_nick = 'pitsxs'
spam_delay = 0.5
should_spam = False
user_api = Api()
app_api = Api()

app = web.Application()
ttv_irc = IRCClient(config.token, nick)
ttv_eventsub = eventsub.EventSub(secret=config.secret,
                                 should_verify_signature=True,
                                 should_limit_time_range=True,
                                 should_control_duplicates=True,
                                 time_limit=10*60,
                                 duplicates_save_period=10*60)


@ttv_irc.event
async def on_message(message):
    global should_spam
    if message.author.login == nick:
        if message.content == '!turn':
            should_spam = False if should_spam else True
        elif message.content == '!once':
            banned_users_agenerator = user_api.get_banned_users(5, ttv_irc.global_state.id)
            banned_users = [banned_user['user_login'] async for banned_user in banned_users_agenerator]
            if test_user_nick in banned_users:
                await ttv_irc.send_message(channel_login=nick, content=f'/unban {test_user_nick}')
            else:
                await ttv_irc.send_message(channel_login=nick, content=f'/ban {test_user_nick}')
        elif message.content == '!unfollow_all':
            async for follow in user_api.get_users_follows(0, from_id=ttv_irc.global_state.id):
                if follow['to_name'] != 'teleq4':
                    await user_api.delete_user_follows(follow['from_id'], follow['to_id'])



@ttv_irc.event
async def on_self_join(channel):
    if channel.login == nick:
        ttv_irc.loop.create_task(ban_unban())


async def ban_unban():
    print('Starting spam')
    rows_s_channel = ttv_irc.get_channel_by_login(nick)
    while True:
        if should_spam:
            await rows_s_channel.send_message(f'/ban {test_user_nick}')
            await asyncio.sleep(spam_delay)
            await rows_s_channel.send_message(f'/unban {test_user_nick}')
            await asyncio.sleep(spam_delay)
        else:
            await asyncio.sleep(spam_delay * 10)


@ttv_eventsub.event
async def on_follow(_, event: eventsub_events.FollowEvent):
    print(f'{event.user_name} has followed to {event.broadcaster_name} at {event.event_time}')
    print(f'id of event is {event.event_id}')


@ttv_eventsub.events('on_ban', 'on_unban')
async def on_ban_type_event(_, event: eventsub_events.BroadcasterUserEventABC):
    event_type = 'banned' if type(event) == eventsub_events.BanEvent else 'unbanned'
    print(f'{event.user_login} was {event_type} in #{event.broadcaster_login} channel')


@ttv_eventsub.event
async def on_verification(sub: eventsub_events.WebhookSubcription):
    print(f'new webhook sub {sub.type}, {sub.condition}, {sub.id}')


async def context(_):
    global app_api, user_api
    await app_api.set_token(config.app_token)
    await user_api.set_token(config.token)
    async for subscription in app_api.get_eventsub_subscriptions(12):
        print(subscription)
        await app_api.delete_eventsub_subscription(subscription['id'])
        print(f"Deleted - {subscription['id']}")
    event_types = ('channel.ban', 'channel.unban')
    callback = 'https://f87c54447562.ngrok.io/twitch/events/subscriptions'
    for event_type in event_types:
        response = await app_api.create_eventsub_subscription(
            type=event_type,
            condition={'broadcaster_user_id': '192827780'},
            callback=callback,
            secret=config.secret
        )
        print(response)
    ttv_eventsub.loop.create_task(ttv_irc.start([config.nick]))


app.add_routes([web.post('/twitch/events/subscriptions', ttv_eventsub.handler)])
app.on_startup.append(context)
web.run_app(app, port=8080)

