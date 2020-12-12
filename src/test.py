import client
import config

bot = client.Client(config.token, config.nick, config.channels)
bot.run()
