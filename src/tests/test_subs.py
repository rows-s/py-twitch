from api import Api
import asyncio

from aiohttp import web

import config
import eventsub
import eventsub_events


app = web.Application()
webhook_handler = eventsub.EventSub(secret=config.secret,
                                    is_verify_signature=True,
                                    is_time_limit_control=True,
                                    is_duplicate_control=True,
                                    time_limit=1*60,
                                    duplicate_save_period=1 * 60)

@webhook_handler.event
async def on_follow(_, event: eventsub_events.FollowEvent):
    print(f'{event.user_name} has followed to {event.broadcaster_user_name} at {event.event_time}')
    print(f'id of event is {event.event_id}')


async def context(app):
    async with Api() as api:
        await api.set_auth(config.app_token)
        async for streams in api.get_streams(12):
            print(streams)
        async for event in api.get_eventsub_subscriptions(12):
            print(event)
            await api.delete_eventsub_subscription(event['id'])
            event_id = event['id']
            print(f'Deleted - {event_id}')

        callback = 'https://e5948344f604.ngrok.io/twitch/events/subscriptions'
        url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
        json = {
            'type': 'channel.follow',
            'version': '1',
            'condition': {
                'broadcaster_user_id': '192827780'
            },
            'transport': {
                'method': 'webhook',
                'callback': callback,
                'secret': config.secret
            }
        }
        response = await api._http_post(url, json, {})
        print(response)
        yield
    print('Now i lay me down to sleep for 31536000 seconds')
    await asyncio.sleep(31536000)


async def on_cleanup(app):
    pass


app.add_routes([web.post('/twitch/events/subscriptions', webhook_handler.handle)])
# app.on_startup.append(on_startup)
# app.on_cleanup.append(on_cleanup)
# app.cleanup_ctx.append(context)
web.run_app(app, port=8080)

