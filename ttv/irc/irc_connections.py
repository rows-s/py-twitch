import asyncio
import logging
from asyncio import Task, create_task
from time import time
from typing import Optional, Union, AsyncGenerator, Callable, Coroutine, Generator, Iterable

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK
from websockets.legacy.client import WebSocketClientProtocol

from .exceptions import CapReqError, LoginFailed
from .irc_messages import IRCMsg, TwitchIRCMsg

__all__ = ('IRCClient', 'irc_connect', 'TTVIRCClient', 'ttv_connect', 'ANON_LOGIN')


ANON_LOGIN = 'justinfan0'


class IRCClient:
    def __init__(
            self,
            uri: str
    ):
        self.is_running: bool = False
        self._uri = uri
        self._ws: WebSocketClientProtocol = WebSocketClientProtocol()
        self._logger = logging.getLogger(__name__)
        self._logger.debug(f'Created {self.__class__.__name__} for uri:{self._uri}')

    @property
    def is_connected(self):
        return self._ws.open

    async def connect(self):
        self._ws = await websockets.connect(self._uri)
        self._logger.info(f'{self.__repr__()} has connected')

    async def send(self, irc_msg: Union[IRCMsg, str]):
        """ Sends <irc_msg> """
        irc_msg = str(irc_msg) + '\r\n'
        await self._ws.send(irc_msg)
        self._logger.debug(f'[{self.__repr__()}] Sending {irc_msg}')

    async def send_msg(self, channel: str, msg: str):
        await self.send(f'PRIVMSG #{channel} :{msg}')

    async def join_channels(self, *channels: str):
        self._logger.debug(f'{self.__repr__()} join {len(channels)} channels')
        if channels:
            logins_str = ',#'.join(channels)
            await self.send(f'JOIN #{logins_str}')

    async def part_channels(self, *channels: str):
        self._logger.debug(f'{self.__repr__()} part {len(channels)} channels')
        if channels:
            logins_str = ',#'.join(channels)
            await self.send(f'PART #{logins_str}')

    async def stop(self, code: int = 1000, reason: str = 'no reason'):
        await self._ws.close(code, reason)
        self._logger.info(f'Connection stoped with code: {code} and reason: {reason}')

    async def __aiter__(self) -> AsyncGenerator[TwitchIRCMsg, None]:
        self.is_running = True
        self._logger.info(f'{self.__repr__()} is running')
        async for raw_irc_msgs in self._ws:
            for raw_irc_msg in raw_irc_msgs.split('\r\n'):
                if not raw_irc_msg:  # skip empty ones
                    continue
                elif raw_irc_msg.startswith('PING'):
                    await self.send(raw_irc_msg.replace('PING', 'PONG', 1))  # saving parts such servername
                    self._logger.debug(f'{self.__repr__()} PING requested. PONG sent')
                else:
                    self._logger.debug(f'{self.__repr__()} got raw_msg: {raw_irc_msg}')
                    yield TwitchIRCMsg(raw_irc_msg)
        self._logger.info(f'{self.__repr__()} successfully stoped')
        self.is_running = False

    def __repr__(self):
        return f'{self.__class__.__name__} ({self._uri})'


async def irc_connect(uri):
    connection = IRCClient(uri)
    await connection.connect()
    return connection


class TTVIRCClient(IRCClient):
    def __init__(
            self,
            login: str,
            token: str,
            *,
            uri: str = 'wss://irc-ws.chat.twitch.tv:443',
            keep_alive: bool = True,
            whisper_agent: str = 'ananonymousgifter',
            on_recconect_callback: Callable[[], Coroutine] = None
    ):
        super().__init__(uri)
        self.login: str = login
        self.token: str = 'oauth:' + token if not token.startswith('oauth:') else token
        self.whisper_agent = whisper_agent

        self.keep_alive: bool = keep_alive
        self._delay_gen = self._delay_gen()  # instance of the generator
        self._restarting_task: Optional[Task] = None
        self.on_recconect_callback: Callable[[], Coroutine] = on_recconect_callback or empty_coroutine
        self._joined_channel_logins: set = set()

    @property
    def is_restarting(self):
        return self._restarting_task is not None

    @property
    def is_anon(self) -> bool:
        return self.login.startswith('justinfan') and not self.login == 'justinfan'

    async def connect(self) -> TwitchIRCMsg:
        self._ws = await websockets.connect(self._uri)
        await self.req_caps('twitch.tv/membership', 'twitch.tv/commands', 'twitch.tv/tags')
        await self.log_in()
        if not self.is_anon:
            return await self._validate_connection()
        else:  # must not have problems with an anon log in
            return IRCMsg.create_empty()

    async def _validate_connection(
            self,
            *,
            expected_commands: Iterable[str] = ('001', '002', '003', '004', '372', '375', '376', 'CAP')
    ) -> TwitchIRCMsg:
        async for irc_msg in self:
            if irc_msg.command == 'GLOBALUSERSTATE':
                if 'user-login' not in irc_msg:
                    irc_msg['user-login'] = self.login
                self._logger.info(f'[{self.__repr__()}] Loged in successfully: {irc_msg}')
                return irc_msg
            elif irc_msg.command == 'NOTICE' and irc_msg.middles[0] == '*':
                self._logger.error(f'[{self.__repr__()}] Loging in failed: {irc_msg}')
                raise LoginFailed(irc_msg.trailing)
            elif irc_msg.command == 'CAP' and irc_msg.middles[1] == 'NAK':
                self._logger.error(f'[{self.__repr__()}] caps request failed: {irc_msg}')
                raise CapReqError(irc_msg)  # too many things base on tags. whatever, it's escapable by try-block
            elif irc_msg.command not in expected_commands:
                self._logger.warning(
                    f'[{self.__repr__()}] skipped validation (unexpected command {irc_msg.command}): {irc_msg}'
                )
                return irc_msg.create_empty()  # we must be logged in if are getting unexpected messages

    async def send(self, irc_msg: Union[IRCMsg, str]):
        """
        Sends :arg:`irc_msg`
        If self.keep_alive ensures that sending <irc_msg> won't be interrupted by :exc:`ConnectionClosed`
        (except :exc:`ConnectionClosedOK`)"""
        while True:
            try:
                return await super().send(str(irc_msg))
            except ConnectionClosedOK:  # instance of :ecx:`ConnectionClosed`
                raise  # inform about messaging through closed ws
            except ConnectionClosed:
                if self.keep_alive:
                    await self.restart()
                else:
                    raise

    async def send_whisper(self, target: str, msg: str, *, through: str = None):
        through = through or self.whisper_agent
        await self.send_msg(through, f'/w {target} {msg}')

    async def join_channels(self, *channels: str):
        self._joined_channel_logins.update(channels)
        await super().join_channels(*channels)
        self._logger.debug(f'actual channels for [{self.__repr__()}] are: {self._joined_channel_logins}')

    async def part_channels(self, *channels: str):
        self._joined_channel_logins.difference_update(channels)
        await super().part_channels(*channels)
        self._logger.debug(f'actual channels for [{self.__repr__()}] are: {self._joined_channel_logins}')

    async def req_caps(self, *caps: str):
        if caps:
            caps_str = ' '.join(caps)
            await self.send(f'CAP REQ :{caps_str}')
            self._logger.debug(f'[{self.__repr__()}] cappabilities requested: {caps_str}')

    async def log_in(self):
        if self.token:  # no PASS for an anon user
            await self.send(f'PASS {self.token}')
        await self.send(f'NICK {self.login}')
        self._logger.debug(f'logging in as {self.login} (anon:{self.is_anon})')

    async def restart(self):
        if not self.is_restarting:
            self._restarting_task = create_task(self._restart())
        await self._restarting_task

    # have to have the func because of the problem that loop.current_task() returns root task, not the last awaited
    async def _restart(self):  # TODO: can stack without any message must be fixed by logging
        self._logger.warning(f'{self.__repr__()} is restarting')
        await asyncio.sleep(next(self._delay_gen))  # realisation of recommended reconnect delays
        await self.connect()
        await self.join_channels(*self._joined_channel_logins)
        asyncio.create_task(self.on_recconect_callback())
        self._running_restart_task = None
        self._logger.warning(f'{self.__repr__()} restarted')

    @classmethod
    def _delay_gen(cls) -> Generator[int, None, None]:
        delay = 0
        while True:
            last_delayed = time()
            yield delay
            # increase
            delay = min(16, max(1, delay * 2))  # if 0 - then 1, no greater then 16
            # reset
            if time() - last_delayed > 60:
                delay = 0  # resetting overwrites the increasing that done anyway

    async def __aiter__(self):
        agen = super().__aiter__()
        while True:
            try:
                yield await agen.__anext__()
            except ConnectionClosed:
                if self.keep_alive:
                    await self.restart()
                else:
                    raise
            except StopAsyncIteration:
                return

    def __repr__(self):
        return f'{super().__repr__()}:({self.login}:{self.token[6:9]})'


async def ttv_connect(login, token, *args, **kwards):
    connection = TTVIRCClient(login, token, *args, **kwards)
    await connection.connect()
    return connection


async def empty_coroutine(*args, **kwargs):
    pass
