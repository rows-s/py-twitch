import asyncio
import os

import websockets
from websockets import ConnectionClosedError
import pytest
from time import sleep, time
from ttv.irc import Client, IRCMessage, Channel
from ttv.irc.exceptions import ChannelNotExists, FunctionIsNotCorutine, UnknownEvent, LoginFailed

irc_token = os.getenv('TTV_IRC_TOKEN')
irc_nick = os.getenv('TTV_IRC_NICK')


def test_event_registration():
    ttv_bot = Client('token', 'login')
    with pytest.raises(FunctionIsNotCorutine):
        @ttv_bot.event
        def on_message(): pass

    with pytest.raises(FunctionIsNotCorutine):
        @ttv_bot.events('on_message')
        def foo(): pass

    with pytest.raises(UnknownEvent):
        @ttv_bot.event
        async def baz(): pass

    with pytest.raises(UnknownEvent):
        @ttv_bot.events('bar')
        async def on_message(): pass

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
    expected = (0, 1, 2, 4, 8, 16, 16, 16, 16)
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
    # LoginFalied
    ttv_bot = Client('token', 'login', should_restart=False)
    with pytest.raises(LoginFailed):
        await ttv_bot.start([])
    # valid one
    valid_bot = Client(irc_token, irc_nick, should_restart=False)
    logged_in = got_join = joined_channel = False

    @valid_bot.event
    async def on_login():
        nonlocal logged_in
        logged_in = True

    @valid_bot.event
    async def on_join(channel: Channel, user_login: str):
        nonlocal got_join
        if user_login == irc_nick:
            got_join = True

    @valid_bot.event
    async def on_self_join(channel: Channel):
        nonlocal joined_channel
        joined_channel = True
        assert channel.login == irc_nick
        assert channel.my_state.is_broadcaster
        assert channel.my_state.display_name.lower() == irc_nick
        assert channel.my_state.badges['broadcaster'] == '1'
        await valid_bot._websocket.close(1000)

    await valid_bot.start([irc_nick])
    assert logged_in
    assert got_join
    assert joined_channel


@pytest.mark.asyncio
async def test_read_websocket():
    # invalid logging
    ttv_bot = Client('token', 'login', should_restart=False)
    await ttv_bot._log_in_irc()
    irc_msgs = (
        IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags'),
        IRCMessage(':tmi.twitch.tv NOTICE * :Login authentication failed')
    )
    index = 0
    async for irc_msg in ttv_bot._read_websocket():
        assert irc_msg == irc_msgs[index]
        index += 1
        if index == len(irc_msgs):
            break
    # connection closed error
    with pytest.raises(websockets.ConnectionClosedError):
        await ttv_bot._websocket.close(3000)
        await ttv_bot._read_websocket().__anext__()
    # coonection closed
    with pytest.raises(StopAsyncIteration):
        ttv_bot._websocket = await websockets.connect('wss://irc-ws.chat.twitch.tv:443')
        assert ttv_bot._websocket.open
        await ttv_bot._websocket.close()
        await ttv_bot._read_websocket().__anext__()
    # valid logging
    valid_bot = Client(irc_token, irc_nick, should_restart=False)
    await valid_bot._log_in_irc()
    irc_msgs = (
        IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags'),
        IRCMessage(f':tmi.twitch.tv 001 {irc_nick} :Welcome, GLHF!'),
        IRCMessage(f':tmi.twitch.tv 002 {irc_nick} :Your host is tmi.twitch.tv'),
        IRCMessage(f':tmi.twitch.tv 003 {irc_nick} :This server is rather new'),
        IRCMessage(f':tmi.twitch.tv 004 {irc_nick} :-'),
        IRCMessage(f':tmi.twitch.tv 375 {irc_nick} :-'),
        IRCMessage(f':tmi.twitch.tv 372 {irc_nick} :You are in a maze of twisty passages, all alike.'),
        IRCMessage(f':tmi.twitch.tv 376 {irc_nick} :>')
    )
    index = 0
    async for irc_msg in valid_bot._read_websocket():
        if index != len(irc_msgs):
            assert irc_msg == irc_msgs[index]
            index += 1
        else:
            assert irc_msg.command == 'GLOBALUSERSTATE'
            assert irc_msg.tags['display-name'].lower() == irc_nick
            break


@pytest.mark.asyncio
async def test_first_log_in_irc():
    ttv_bot = Client('token', 'login', should_restart=False)
    with pytest.raises(LoginFailed):
        await ttv_bot._first_log_in_irc()

    valid_bot = Client(irc_token, irc_nick, should_restart=False)
    logined = False

    @valid_bot.event
    async def on_login():
        nonlocal logined
        logined = True

    await valid_bot._first_log_in_irc()
    await asyncio.sleep(0.01)  # on_login is delayed (task created not called) here we let other tasks work
    assert logined


# @pytest.mark.asyncio
# async def test_restart():
#     valid_bot = Client(irc_token, irc_nick, should_restart=False)
#     valid_bot.joined_channel_logins.add(irc_nick)
#     is_reconnected = is_joined = False
#
#     @valid_bot.event
#     async def on_reconnect():
#         nonlocal is_reconnected
#         is_reconnected = True
#
#     @valid_bot.event
#     async def on_self_join():
#         nonlocal is_joined
#         is_joined = True
#
#     async def handler():
#         async for irc_msg in valid_bot._read_websocket():
#             await valid_bot._handle_command(irc_msg)
#
#     asyncio.get_event_loop().create_task(handler())
#     for delay in (0, 1, 2, 4, 8, 16, 16):
#         t0 = time()
#         await valid_bot.restart()
#         assert delay - 0.2 < time() - t0 < delay + 5  # might sleep less than specified
#         await asyncio.sleep(0.1)
#         assert is_reconnected
#         assert is_joined
#         is_reconnected = False
#         is_joined = False
#         valid_bot._channels_by_login.pop(irc_nick)




