import asyncio
import os

import websockets
from websockets import ConnectionClosedError
import pytest
from time import sleep, time
from ttv.irc import Client, IRCMessage, Channel, GlobalState, LocalState
from ttv.irc.exceptions import ChannelNotPrepared, FunctionIsNotCorutine, UnknownEvent, LoginFailed, CapabilitiesReqError

IRC_TOKEN = os.getenv('TTV_IRC_TOKEN')
IRC_USERNAME = os.getenv('TTV_IRC_NICK')
IRC_URI = 'wss://irc-ws.chat.twitch.tv:443'


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
    channel = Channel({'room-id': '0123', 'room-login': 'login'}, lambda _: None)
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
    assert ttv_bot._get_prepared_channel(channel.login) is channel
    with pytest.raises(ChannelNotPrepared):
        ttv_bot._get_prepared_channel('')


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
                sleep(60.2)  # TODO: it's not good waiting 60 seconds
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
    valid_bot = Client(IRC_TOKEN, IRC_USERNAME, should_restart=False)
    logged_in = got_join = joined_channel = False

    @valid_bot.event
    async def on_login():
        nonlocal logged_in
        logged_in = True

    @valid_bot.event
    async def on_join(channel: Channel, user_login: str):
        nonlocal got_join
        if user_login == IRC_USERNAME:
            got_join = True

    @valid_bot.event
    async def on_self_join(channel: Channel):
        nonlocal joined_channel
        joined_channel = True
        assert channel.login == IRC_USERNAME
        assert channel.my_state.is_broadcaster
        assert channel.my_state.display_name.lower() == IRC_USERNAME
        assert channel.my_state.badges['broadcaster'] == '1'
        await valid_bot._websocket.close(1000)

    await valid_bot.start([IRC_USERNAME])
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
        ttv_bot._websocket = await websockets.connect(IRC_URI)
        assert ttv_bot._websocket.open
        await ttv_bot._websocket.close()
        await ttv_bot._read_websocket().__anext__()
    # valid logging
    valid_bot = Client(IRC_TOKEN, IRC_USERNAME, should_restart=False)
    await valid_bot._log_in_irc()
    irc_msgs = (
        IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags'),
        IRCMessage(f':tmi.twitch.tv 001 {IRC_USERNAME} :Welcome, GLHF!'),
        IRCMessage(f':tmi.twitch.tv 002 {IRC_USERNAME} :Your host is tmi.twitch.tv'),
        IRCMessage(f':tmi.twitch.tv 003 {IRC_USERNAME} :This server is rather new'),
        IRCMessage(f':tmi.twitch.tv 004 {IRC_USERNAME} :-'),
        IRCMessage(f':tmi.twitch.tv 375 {IRC_USERNAME} :-'),
        IRCMessage(f':tmi.twitch.tv 372 {IRC_USERNAME} :You are in a maze of twisty passages, all alike.'),
        IRCMessage(f':tmi.twitch.tv 376 {IRC_USERNAME} :>')
    )
    index = 0
    async for irc_msg in valid_bot._read_websocket():
        if index != len(irc_msgs):
            assert irc_msg == irc_msgs[index]
            index += 1
        else:
            assert irc_msg.command == 'GLOBALUSERSTATE'
            assert irc_msg.tags['display-name'].lower() == IRC_USERNAME  # would work only with latin names
            break


@pytest.mark.asyncio
async def test_first_log_in_irc():
    ttv_bot = Client('token', 'login', should_restart=False)
    with pytest.raises(LoginFailed):
        await ttv_bot._first_log_in_irc()
    with pytest.raises(CapabilitiesReqError):
        ttv_bot._websocket = await websockets.connect(IRC_URI)
        await ttv_bot._send('CAP REQ :ttv.tv/membership ttv.tv/commands ttv.tv/tags')  # !ttv.tv!
        await ttv_bot._first_log_in_irc()

    valid_bot = Client(IRC_TOKEN, IRC_USERNAME, should_restart=False)
    logined = False

    @valid_bot.event
    async def on_login():
        nonlocal logined
        logined = True

    await valid_bot._first_log_in_irc()
    await asyncio.sleep(0.01)  # on_login is delayed (task created not called) here we let other tasks work
    assert logined


@pytest.mark.asyncio
async def test_restart():
    valid_bot = Client(IRC_TOKEN, IRC_USERNAME)
    is_loged_in = False
    is_reconnected = False
    is_joined = False
    is_updated = False
    is_global_state_updated = False
    is_local_state_updated = False
    is_nameslist_updated = False

    @valid_bot.event
    async def on_login():
        nonlocal is_loged_in
        assert not is_loged_in
        is_loged_in = True
        assert valid_bot.is_running

    @valid_bot.event
    async def on_reconnect():
        nonlocal is_reconnected
        is_reconnected = True

    @valid_bot.event
    async def on_self_join(channel: Channel):
        nonlocal is_joined
        assert not is_joined
        is_joined = True
        assert channel.login == IRC_USERNAME
        assert channel.my_state.is_broadcaster

    @valid_bot.event
    async def on_channel_update(before: Channel, after: Channel):
        nonlocal is_updated
        is_updated = True
        assert before.login == after.login == IRC_USERNAME
        assert before.my_state.display_name.lower() == after.my_state.display_name.lower() == IRC_USERNAME

    @valid_bot.event
    async def on_global_state_update(before: GlobalState, after: GlobalState):
        nonlocal is_global_state_updated
        is_global_state_updated = True
        assert before.login == after.login == IRC_USERNAME

    @valid_bot.event
    async def on_my_state_update(channel: Channel, before: LocalState, after: LocalState):
        nonlocal is_local_state_updated
        is_local_state_updated = True
        assert channel.login == IRC_USERNAME
        assert before.login == after.login == IRC_USERNAME
        assert before.is_broadcaster and after.is_broadcaster

    @valid_bot.event
    async def on_nameslist_update(channel: Channel, before, after):
        nonlocal is_nameslist_updated
        is_nameslist_updated = True
        assert channel.login == IRC_USERNAME
        assert IRC_USERNAME in before and IRC_USERNAME in after

    valid_bot.loop.create_task(valid_bot.start([IRC_USERNAME]))
    await asyncio.sleep(5)  # let the task work

    for delay in (0, 1, 2, 4, 8, 16, 16):
        await valid_bot._websocket.close(3000)  # restart will be called within start()
        # 40 (280) retests (restarts) was passed in a row with 20 seconds delay.
        await asyncio.sleep(delay + 20)  # delay + time for handlers (had troubles using 15 and less)
        assert is_loged_in
        assert is_joined
        assert is_reconnected
        is_reconnected = False
        assert is_updated
        is_updated = False
        assert is_global_state_updated
        is_global_state_updated = False
        assert is_local_state_updated
        is_local_state_updated = False
        assert is_nameslist_updated
        is_nameslist_updated = False


@pytest.mark.asyncio
def test_handle_command():
    pass
    # delay msg
    # on_unknown_command