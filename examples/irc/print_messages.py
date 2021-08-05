import os

from ttv.irc import Client, ChannelMessage

TOKEN = os.environ['TTV_IRC_TOKEN']
USERNAME = os.environ['TTV_IRC_NICK']
bot = Client(TOKEN, USERNAME)


@bot.event
async def on_ready():
    print(f'Ready as @{bot.login} ({bot.global_state.id})')


@bot.event
async def on_message(message: ChannelMessage):
    print(message)
    if message.author.login == bot.login:
        if message.content == '!stop':
            await bot.stop()

bot.run([USERNAME])
