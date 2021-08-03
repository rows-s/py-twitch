from ttv.irc import Client, ANON_TOKEN, ANON_LOGIN


class Bot(Client):
    async def on_message(self, message):
        print(message)


Bot(ANON_TOKEN, ANON_LOGIN).run(['ananonymousgifter'])  # send a message to https://www.twitch.tv/ananonymousgifter
