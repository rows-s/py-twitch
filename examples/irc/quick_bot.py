from ttv.irc import Client


class Bot(Client):
    async def on_message(self, message):
        print(message)


Bot('', 'justinfan0').run(['ananonymousgifter'])  # send a message to https://www.twitch.tv/ananonymousgifter
