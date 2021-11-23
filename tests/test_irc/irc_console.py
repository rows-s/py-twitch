import asyncio
import os

from aioconsole import ainput

from ttv.irc import Client, ANON_LOGIN


class IRCConsole(Client):
    async def start_(self):
        self._start_task = asyncio.create_task(self.listen())
        await asyncio.gather(self._start_task, self.run_console())

    async def listen(self):
        await self.irc_connection.connect()
        try:
            async for irc_msg in self.irc_connection:
                if irc_msg.command == 'PING':
                    self._handle_ping(irc_msg)
                print(irc_msg)
        except asyncio.exceptions.CancelledError:
            pass

    async def run_console(self):
        while True:
            raw_irc_msg = await ainput()
            if raw_irc_msg == 'stop':
                self._start_task.cancel()
                return
            else:
                await self._send(raw_irc_msg)
                await asyncio.sleep(0.5)


if __name__ == '__main__':
    TOKEN = os.getenv('TTV_IRC_TOKEN', '')
    LOGIN = os.getenv('TTV_IRC_NICK', ANON_LOGIN)

    # irc_console_client = IRCConsole('', 'justinfan0')
    irc_console_client = IRCConsole(TOKEN, LOGIN)

    @irc_console_client.event
    async def on_reconnect(): print('\n\nRESTARTED\n\n')

    loop = asyncio.get_event_loop().run_until_complete(irc_console_client.start_())
