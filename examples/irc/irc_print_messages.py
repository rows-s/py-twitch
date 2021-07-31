import os

from ttv.irc import Client, ChannelMessage

TOKEN = os.environ['TTV_IRC_TOKEN']
USERNAME = os.environ['TTV_IRC_NICK']
bot = Client(TOKEN, USERNAME)


@bot.event
async def on_ready():
    print(f'Ready to listen the chat as @{bot.global_state.login}')


@bot.event
async def on_message(message: ChannelMessage):
    print(f'@{message.author.login} in #{message.channel.login} :{message.content}')
    if message.author.login == bot.login:
        if message.content == '!stop':
            await bot.stop()


@bot.event
async def on_notice(channel, notice_id, text):
    print(f'#{channel}, {notice_id}, :{text}')


bot.run([USERNAME])
