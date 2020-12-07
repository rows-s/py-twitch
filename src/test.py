import client
import config
import asyncio

bot = client.Client(config.token, config.nick, config.channels)
bot.run()
