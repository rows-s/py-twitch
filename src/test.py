import client
import config

class MyBot(client.Client):
    pass

bot = MyBot(config.token, config.nick, config.channels)

@bot.event
async def on_room_update(before, after):
    print('!!!!We got info about changes')
    print(before, after, sep='\n')

@bot.event
async def on_room_join(channel: client.Channel):
    await channel.send('Bot has been planted')
    # await channel.clear()
    # await channel.send('Bot had delete all before it been planted')
    
bot.run()
