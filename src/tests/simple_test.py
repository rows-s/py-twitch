from ..irc_client import Client
from .. import config

bot = Client(config.token, config.nick)

bot.run(['rows_s'])
