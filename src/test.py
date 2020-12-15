import client
import config

class MyBot(client.Client):
    pass

bot = MyBot(config.token, config.nick)

@bot.event
async def on_room_update(before, after):
    print('!!!!We got info about changes')
    print(before, after, sep='\n')

# @bot.event
# async def on_room_join(channel: client.Channel):
#     await channel.send('Bot has been planted')
#     # await channel.clear()
#     # await channel.send('Bot had delete all before it been planted')
@bot.event
async def on_message(message: client.Message):
    channel = message.channel.name
    author = message.author.name
    text = message.content
    print(f'In #{channel}, user {author} wrote: {text}')

@bot.event
async def on_login(self: client.Client):
    name = self.name
    color = self.color
    id = self.id
    emotes = self.emotes
    print('succesfull loggin in')
    
bot.run(config.channels)
