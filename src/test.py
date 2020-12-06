import client
import config
import asyncio

bot = client.Client(config.token, config.nick, config.channels)

asyncio.get_event_loop().run_until_complete(bot.run())
