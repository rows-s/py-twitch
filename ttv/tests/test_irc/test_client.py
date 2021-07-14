import websockets
import pytest
from time import sleep
from ttv.irc import Client, IRCMessage, Channel
from ttv.irc.exceptions import ChannelNotExists, FunctionIsNotCorutine, UnknownEvent, LoginFailed


def test_event_registration():
    ttv_bot = Client('token', 'login')
    with pytest.raises(FunctionIsNotCorutine):
        @ttv_bot.event
        def on_message():
            pass

    with pytest.raises(FunctionIsNotCorutine):
        @ttv_bot.events('on_message')
        def foo():
            pass

    with pytest.raises(UnknownEvent):
        @ttv_bot.event
        async def baz():
            pass

    with pytest.raises(UnknownEvent):
        @ttv_bot.events('bar')
        async def on_message():
            pass

    @ttv_bot.event
    async def on_message(): pass
    assert hasattr(ttv_bot, 'on_message')

    @ttv_bot.events('on_join', 'on_part')
    async def any_name(): pass
    assert hasattr(ttv_bot, 'on_join') and hasattr(ttv_bot, 'on_part')


def test_channel_getters():
    ttv_bot = Client('token', 'login')
    channel = Channel(lambda _: None, {'room-id': '0123', 'room-login': 'login'})
    ttv_bot._channels_by_id[channel.id] = channel
    ttv_bot._channels_by_login[channel.login] = channel
    # id
    assert ttv_bot.get_channel_by_id(channel.id) is channel
    assert ttv_bot.get_channel_by_id('') is None
    assert ttv_bot.get_channel_by_id('', channel) is channel
    # login
    assert ttv_bot.get_channel_by_login(channel.login) is channel
    assert ttv_bot.get_channel_by_login('') is None
    assert ttv_bot.get_channel_by_login('', channel) is channel
    # if exists
    assert ttv_bot._get_channel_if_exists(channel.login) is channel
    with pytest.raises(ChannelNotExists):
        ttv_bot._get_channel_if_exists('')


def test_get_reconnect_delay():
    ttv_bot = Client('token', 'login')
    expected = (0, 1, 2, 4, 8, 8, 8, 8, 8)
    has_sleept = False
    index = 0
    for delay in ttv_bot._delay_gen:
        if index != len(expected):
            assert delay == expected[index]
            index += 1
        else:
            if not has_sleept:
                sleep(61)  # TODO: it's not good waiting 60 seconds
                has_sleept = True
            else:
                assert delay == 0
                break


@pytest.mark.asyncio
async def test_start():
    ttv_bot = Client('token', 'login', should_restart=False)
    with pytest.raises(LoginFailed):
        await ttv_bot.start([])


@pytest.mark.asyncio
async def test_read_websocket():
    ttv_bot = Client('token', 'login', should_restart=False)
    await ttv_bot._log_in_irc()
    capabilities = IRCMessage(':tmi.ttv.tv CAP * ACK :ttv.tv/membership ttv.tv/commands ttv.tv/tags')
    login_failed = IRCMessage(':tmi.ttv.tv NOTICE * :Login authentication failed')
    irc_msgs = (capabilities, login_failed)
    index = 0
    async for irc_msg in ttv_bot._read_websocket():
        # irc_msgs.append(irc_msg)
        assert irc_msg == irc_msgs[index]
        index += 1
        if index == len(irc_msgs):
            break
    with pytest.raises(websockets.ConnectionClosedError):
        await ttv_bot._websocket.close(3000)
        await ttv_bot._read_websocket().__anext__()


@pytest.mark.asyncio
async def test_first_log_in_irc():
    ttv_bot = Client('token', 'login', should_restart=False)
    # logined = False
    with pytest.raises(LoginFailed):
        await ttv_bot._first_log_in_irc()
    #
    # @ttv_bot.event
    # async def on_login():
    #     nonlocal logined
    #     logined = True
    #
    # await ttv_bot._first_log_in_irc()
    # assert logined

