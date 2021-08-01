import asyncio
import os
from typing import Tuple, Iterable

import websockets
import pytest
from time import sleep, time
from ttv.irc import Client, IRCMessage, Channel, GlobalState, LocalState, ChannelMessage, Whisper
from ttv.irc.exceptions import *

IRC_TOKEN = os.getenv('TTV_IRC_TOKEN')
IRC_USERNAME = os.getenv('TTV_IRC_NICK')
IRC_URI = 'wss://irc-ws.chat.twitch.tv:443'
should_skip_long_tests = True


def test_event_registration():
    ttv_bot = Client('token', 'login')
    with pytest.raises(TypeError):
        @ttv_bot.event
        def on_message(): pass

    with pytest.raises(NameError):
        @ttv_bot.event
        async def baz(): pass

    @ttv_bot.event
    async def on_message(): pass
    assert hasattr(ttv_bot, 'on_message')


def test_channel_getters():
    ttv_bot = Client('token', 'login')
    channel = Channel(
        IRCMessage('@room-id=0123;room-login=login E'), LocalState(IRCMessage('N')), tuple(), lambda _: None
    )
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
    # login or id
    assert ttv_bot.get_channel(channel.login) is channel
    assert ttv_bot.get_channel(channel.id) is channel
    # if exists
    assert ttv_bot._get_prepared_channel(channel.login) is channel
    with pytest.raises(ChannelNotPrepared):
        ttv_bot._get_prepared_channel('')


@pytest.mark.skipif(should_skip_long_tests, reason='Skipped as a long test')
def test_get_reconnect_delay():
    ttv_bot = Client('token', 'login')
    expected = (0, 1, 2, 4, 8, 16, 16, 16, 16)
    has_slept = False
    index = 0
    for delay in ttv_bot._delay_gen:
        if index != len(expected):
            assert delay == expected[index]
            index += 1
        else:
            if not has_slept:
                sleep(60.2)  # TODO: it's not good waiting 60 seconds
                has_slept = True
            else:
                assert delay == 0
                break


@pytest.mark.asyncio
async def test_start():
    # LoginFailed
    ttv_bot = Client('token', 'login', should_restart=False)
    with pytest.raises(LoginFailed):
        await ttv_bot.start([])
    # valid one
    valid_bot = Client(IRC_TOKEN, IRC_USERNAME, should_restart=False)
    logged_in = got_join = joined_channel = False

    @valid_bot.event
    async def on_ready():
        nonlocal logged_in
        logged_in = True

    @valid_bot.event
    async def on_user_join(channel: Channel, user_login: str):
        nonlocal got_join
        if user_login == IRC_USERNAME and channel.login == IRC_USERNAME:
            got_join = True

    @valid_bot.event
    async def on_channel_join(channel: Channel):
        nonlocal joined_channel
        if channel.login == IRC_USERNAME and channel.client_state.is_broadcaster:
            if channel.client_state.login == IRC_USERNAME:
                joined_channel = True
        await valid_bot._websocket.close(1000)

    await valid_bot.start([IRC_USERNAME])  # will be finished in `on_channel_join()`
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
    # connection closed
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
    async def on_ready():
        nonlocal logined
        logined = True

    await valid_bot._first_log_in_irc()
    await asyncio.sleep(0.01)  # on_ready is delayed (task created not called) here we let other tasks work
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
    async def on_ready():
        nonlocal is_loged_in
        assert not is_loged_in
        assert valid_bot.is_running
        is_loged_in = True

    @valid_bot.event
    async def on_reconnect():
        nonlocal is_reconnected
        is_reconnected = True

    @valid_bot.event
    async def on_channel_join(channel: Channel):
        nonlocal is_joined
        assert not is_joined
        assert channel.login == IRC_USERNAME
        assert channel.client_state.is_broadcaster
        is_joined = True

    @valid_bot.event
    async def on_channel_update(before: Channel, after: Channel):
        nonlocal is_updated
        assert before.login == after.login == IRC_USERNAME
        assert before.client_state.login == after.client_state.login == IRC_USERNAME
        is_updated = True

    @valid_bot.event
    async def on_global_state_update(before: GlobalState, after: GlobalState):
        nonlocal is_global_state_updated
        assert before.login == after.login == IRC_USERNAME
        is_global_state_updated = True

    @valid_bot.event
    async def on_local_state_update(channel: Channel, before: LocalState, after: LocalState):
        nonlocal is_local_state_updated
        assert channel.login == before.login == after.login == IRC_USERNAME
        assert before.is_broadcaster and after.is_broadcaster
        is_local_state_updated = True

    @valid_bot.event
    async def on_names_update(channel: Channel, before, after):
        nonlocal is_nameslist_updated
        assert channel.login == IRC_USERNAME
        assert IRC_USERNAME in before and IRC_USERNAME in after
        is_nameslist_updated = True

    valid_bot.loop.create_task(valid_bot.start([IRC_USERNAME]))
    await asyncio.sleep(2)  # let the task work

    await valid_bot._websocket.close(3000)  # restart will be called by start()
    await asyncio.sleep(0.001)
    assert valid_bot.is_restarting
    await valid_bot._running_restart_task
    assert not valid_bot.is_restarting
    await asyncio.sleep(2)
    assert is_loged_in
    assert is_joined
    assert is_reconnected
    assert is_updated
    assert is_global_state_updated
    assert is_local_state_updated
    assert is_nameslist_updated

CAP = IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
GS = IRCMessage('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 GLOBALUSERSTATE')
RS = IRCMessage('@emote-only=0;followers-only=-1;r9k=0;rituals=0;room-id=12345;slow=0;subs-only=0 ROOMSTATE #target')
NP = IRCMessage('353 #target :username username2 username3')
NP2 = IRCMessage('353 #target :username4 username5 username6')
NAMES = ['username', 'username2', 'username3'] + ['username4', 'username5', 'username6']
NE = IRCMessage('366 #target')
LS = IRCMessage('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 USERSTATE #target')
MSG = IRCMessage('@badges=moderator/1,subscriber/2;@badge-info=subscriber/7;color=#FFFFFF;display-name=UserName;'
                 'emotes=555555558:23-24;flags=;'
                 'tmi-sent-ts=1627200608549;id=4678496c-3fcd-4ae5-90c0-e85cd15bd81d;room-id=12345;user-id=98765;'
                 'user-type=;bits= '
                 ':username!username@username PRIVMSG #target :content with a @metion :(')


async def handle_commands(client: Client, irc_msgs: Iterable[IRCMessage]):
    for irc_msg in irc_msgs:
        await client._handle_command(irc_msg)


@pytest.mark.asyncio
async def test_handle_command():
    pass
    # delay msg
    privmsg = IRCMessage(':fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv PRIVMSG #taget :@some_user text')
    ttv_bot = Client('token', 'login')
    @ttv_bot.event
    async def on_message(_): pass
    await ttv_bot._handle_command(privmsg)
    assert ttv_bot._delayed_irc_msgs['axozer'] == [privmsg]
    # on_unknown_command
    is_on_unknown_command_called = False

    @ttv_bot.event
    async def on_unknown_command(irc_msg: IRCMessage):
        nonlocal is_on_unknown_command_called
        assert irc_msg is CAP
        is_on_unknown_command_called = True

    await ttv_bot._handle_command(CAP)
    await asyncio.sleep(0.001)
    assert is_on_unknown_command_called
    # also is being tested in test_handle_* tests


@pytest.mark.asyncio
async def test_handle_names_part():
    ttv_bot = Client('token', 'login')
    # set(update)
    await ttv_bot._handle_command(NP)
    assert ttv_bot._channels_accumulator.names[NP.channel] == NAMES[:3]
    # update
    await ttv_bot._handle_command(NP2)
    assert ttv_bot._channels_accumulator.pop_names(NP2.channel) == tuple(NAMES)


@pytest.mark.asyncio
async def test_handle_names_end():
    ttv_bot = Client('token', 'login')
    # end
    await handle_commands(ttv_bot, [NP, NE])
    assert ttv_bot._channels_accumulator.pop_names(NE.channel) == ('username', 'username2', 'username3')
    # also is being tested in `test_handle_names_update()`


@pytest.mark.asyncio
async def test_handle_names_update():
    ttv_bot = Client('token', 'login')
    is_names_updated = False

    @ttv_bot.event
    async def on_names_update(channel: Channel, _: Tuple, __: Tuple):
        nonlocal is_names_updated
        if channel.login == 'username':
            is_names_updated = True

    ttv_bot._channels_by_login['username'] = Channel(
        IRCMessage('@room-login=username E'), LocalState(IRCMessage('N')), tuple(), lambda: None
    )
    # end
    irc_msg_nmsp = IRCMessage(':username.tmi.twitch.tv 353 username = #username :username username2 username3')
    irc_msg_nmse = IRCMessage(':username.tmi.twitch.tv 366 username #username :End of /NAMES list')
    await ttv_bot._handle_command(irc_msg_nmsp)
    await ttv_bot._handle_command(irc_msg_nmse)
    assert ttv_bot.get_channel_by_login(irc_msg_nmse.channel).names == ('username', 'username2', 'username3')
    await asyncio.sleep(0.001)
    assert is_names_updated


@pytest.mark.asyncio
async def test_handle_roomstate():
    ttv_bot = Client('token', 'login')
    irc_msg_rs = IRCMessage(
        '@emote-only=0;followers-only=0;r9k=0;rituals=0;room-id=0;slow=0;subs-only=0 :tmi.twitch.tv ROOMSTATE #rows_s'
    )
    await ttv_bot._handle_command(irc_msg_rs)
    assert ttv_bot._channels_accumulator.channel_states[irc_msg_rs.channel] is irc_msg_rs
    # also is being tested in `test_handle_channel_update()`


@pytest.mark.asyncio
async def test_handle_channel_update():
    ttv_bot = Client('token', 'login')
    is_channel_updated = False

    @ttv_bot.event
    async def on_channel_update(before: Channel, after: Channel):
        nonlocal is_channel_updated
        if before.login == after.login == 'username' and not before.is_emote_only and after.is_emote_only:
            is_channel_updated = True
    IRCMessage('@room-login=login E')
    ttv_bot._channels_by_login['username'] = Channel(
        IRCMessage('@room-login=username E'), LocalState(IRCMessage('N')), tuple(), lambda: None
    )
    irc_msg_rsu = IRCMessage('@emote-only=1 :tmi.twitch.tv ROOMSTATE #username')
    await ttv_bot._handle_command(irc_msg_rsu)
    assert ttv_bot.get_channel_by_login(irc_msg_rsu.channel).is_emote_only
    await asyncio.sleep(0.001)
    assert is_channel_updated
    # end


@pytest.mark.asyncio
async def test_handle_userstate_update():
    ttv_bot = Client('token', 'login')
    irc_msg_gus = IRCMessage('@user-id=10;user-login=username :tmi.twitch.tv GLOBALUSERSTATE')
    await ttv_bot._handle_command(irc_msg_gus)
    irc_msg_us = IRCMessage('@badges=broadcaster/1 :tmi.twitch.tv USERSTATE #username')
    await ttv_bot._handle_command(irc_msg_us)
    assert ttv_bot._channels_accumulator.client_states[irc_msg_us.channel] == irc_msg_us


@pytest.mark.asyncio
async def test_handle_userstate_update():
    ttv_bot = Client('token', 'login')
    irc_msg_gus = IRCMessage('@user-id=10;user-login=username :tmi.twitch.tv GLOBALUSERSTATE')
    await ttv_bot._handle_command(irc_msg_gus)
    is_userstate_updated = False
    
    @ttv_bot.event
    async def on_local_state_update(channel: Channel, before: LocalState, after: LocalState):
        nonlocal is_userstate_updated
        if channel.login == 'username':
            if before.login == after.login == 'username':
                if not before.is_broadcaster and after.is_broadcaster:
                    is_userstate_updated = True

    ttv_bot._channels_by_login['username'] = Channel(
        IRCMessage('@room-login=username R'), LocalState(IRCMessage('@user-login=username L')), tuple(), lambda: None)
    irc_msg_usu = IRCMessage('@badges=broadcaster/1 :tmi.twitch.tv USERSTATE #username')
    await ttv_bot._handle_command(irc_msg_usu)
    assert ttv_bot.get_channel_by_login(irc_msg_usu.channel).client_state.is_broadcaster
    await asyncio.sleep(0.001)
    assert is_userstate_updated
    

@pytest.mark.asyncio
async def test_handle_privmsg():
    ttv_bot = Client('token', 'login')
    did_handle_message = False

    @ttv_bot.event
    async def on_message(msg: ChannelMessage):
        nonlocal did_handle_message
        assert msg.channel.login == 'target'
        assert msg.content == 'content of the message'
        assert msg.author.login == 'login' and msg.author.display_name == 'LoGiN'
        assert not msg.is_reply
        did_handle_message = True

    ttv_bot._channels_by_login['target'] = Channel(IRCMessage('@room-login=target ROOMSTATE #target'),
                                                   LocalState(IRCMessage('N')), tuple(), lambda: None)
    irc_msg_privmsg = IRCMessage('@display-name=LoGiN :login!login@login PRIVMSG #target :content of the message')
    await ttv_bot._handle_command(irc_msg_privmsg)
    await asyncio.sleep(0.001)
    assert did_handle_message


@pytest.mark.asyncio
async def test_handle_whisper():
    ttv_bot = Client('token', 'login')
    did_handle_whisper = False

    @ttv_bot.event
    async def on_whisper(wisper: Whisper):
        assert wisper.author.login == 'login'
        assert wisper.content == 'content of the whisper'
        assert wisper.id == '12'
        assert wisper.thread_id == '1_2'
        nonlocal did_handle_whisper
        did_handle_whisper = True

    irc_msg_whisper = IRCMessage('@message-id=12;thread-id=1_2 :login!login@login WHISPER :content of the whisper')
    await ttv_bot._handle_command(irc_msg_whisper)
    await asyncio.sleep(0.001)
    assert did_handle_whisper


@pytest.mark.asyncio
async def test_handle_join():
    ttv_bot = Client('token', 'login')
    did_join = False

    @ttv_bot.event
    async def on_user_join(channel: Channel, login: str):
        assert channel.login == 'target'
        assert login == 'login'
        nonlocal did_join
        did_join = True
    ttv_bot._channels_by_login['target'] = Channel(IRCMessage('@room-login=target ROOMSTATE #target'),
                                                   LocalState(IRCMessage('N')), tuple(), lambda: None)
    irc_msg_join = IRCMessage(':login!login@login JOIN #target')
    await ttv_bot._handle_command(irc_msg_join)
    await asyncio.sleep(0.001)
    assert did_join


@pytest.mark.asyncio
async def test_handle_part():
    ttv_bot = Client('token', 'login')
    did_part = False

    @ttv_bot.event
    async def on_user_part(channel: Channel, login: str):
        assert channel.login == 'target'
        assert login == 'login'
        nonlocal did_part
        did_part = True
    ttv_bot._channels_by_login['target'] = Channel(IRCMessage('@room-login=target ROOMSTATE #target'),
                                                   LocalState(IRCMessage('N')), tuple(), lambda: None)
    irc_msg_part = IRCMessage(':login!login@login PART #target')
    await ttv_bot._handle_command(irc_msg_part)
    await asyncio.sleep(0.001)
    assert did_part
