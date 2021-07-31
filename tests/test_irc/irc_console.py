import asyncio
import os

from ttv.irc import Client
from aioconsole import ainput


class IRCConsole(Client):
    async def start_(self):
        self._start_task = self.listen()
        await asyncio.gather(self._start_task, self.run_console())

    async def listen(self):
        await self._log_in_irc()
        async for irc_msg in self._read_websocket():
            if irc_msg.command == 'PING':
                self._handle_ping(irc_msg)
            print(irc_msg)

    async def run_console(self):
        while True:
            raw_irc_msg = await ainput("IRC message: ")
            if raw_irc_msg == 'stop':
                self._start_task.close()
                return
            else:
                await self._send(raw_irc_msg)
                await asyncio.sleep(0.5)


if __name__ == '__main__':
    IRC_TOKEN = os.environ['TTV_IRC_TOKEN']
    IRC_NICK = os.environ['TTV_IRC_NICK']

    # irc_console_client = IRCConsole('', 'justinfan0')
    irc_console_client = IRCConsole(IRC_TOKEN, IRC_NICK)

    @irc_console_client.event
    async def on_reconnect(): print('\n\nRESTARTED\n\n')

    loop = asyncio.get_event_loop().run_until_complete(irc_console_client.start_())
