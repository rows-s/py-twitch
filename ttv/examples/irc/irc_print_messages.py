import config
from ttv.irc import Client, ChannelMessage

ttv_chat_bot = Client(config.token, config.nick)


@ttv_chat_bot.event
async def on_message(message: ChannelMessage):
    print(f'@{message.author.login} in #{message.channel.login} :{message.content}')


@ttv_chat_bot.event
async def on_notice(channel, notice_id, text):
    print(f'#{channel}, {notice_id}, :{text}')


ttv_chat_bot.run((config.nick,))
