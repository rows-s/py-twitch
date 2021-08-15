import asyncio
import os
from time import sleep
from typing import Tuple, Optional

import pytest
import websockets

from tests.test_irc.irc_msgs import *  # TODO: bad import
from ttv.irc import Client, Channel, GlobalState, LocalState, ChannelMessage, Whisper
from ttv.irc.events import OnNotice, OnChannelJoinError, OnSendMessageError, OnUserBan, OnUserTimeout, OnClearChat, \
    OnMessageDelete
from ttv.irc.exceptions import *

IRC_TOKEN = os.getenv('TTV_IRC_TOKEN')
IRC_USERNAME = os.getenv('TTV_IRC_NICK')
IRC_URI = 'wss://irc-ws.chat.twitch.tv:443'
should_skip_long_tests = True


def test_event_registration():
    bot = Client('token', 'login')
    with pytest.raises(TypeError):
        @bot.event
        def on_message(): pass

    with pytest.raises(NameError):
        @bot.event
        async def baz(): pass

    @bot.event
    async def on_message(): pass
    assert hasattr(bot, 'on_message')


@pytest.mark.asyncio
async def test_channel_getters():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.channel = None

        async def on_channel_join(self, channel: Channel):
            self.channel = channel

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS)  # set global_state, ACCUMUATE THE CHANNEL
    await asyncio.sleep(0.01)  # call the event
    # id
    assert bot.get_channel_by_id('12345') is bot.channel
    assert bot.get_channel_by_id('') is None
    assert bot.get_channel_by_id('', 'DEFAULT') is 'DEFAULT'
    # login
    assert bot.get_channel_by_login('target') is bot.channel
    assert bot.get_channel_by_login('') is None
    assert bot.get_channel_by_login('', 'DEFAULT') is 'DEFAULT'
    # login or id
    assert bot.get_channel('target') is bot.channel
    assert bot.get_channel('12345') is bot.channel
    # if exists
    assert bot._get_prepared_channel('target') is bot.channel
    with pytest.raises(ChannelNotPrepared):
        bot._get_prepared_channel('')


@pytest.mark.skipif(should_skip_long_tests, reason='Skipped as a long test')
def test_get_reconnect_delay():
    bot = Client('token', 'login')
    expected = (0, 1, 2, 4, 8, 16, 16, 16, 16)
    has_slept = False
    index = 0
    for delay in bot._delay_gen:
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
    bot = Client('token', 'login')
    with pytest.raises(LoginFailed):
        await bot.start([])

    # Valid test
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.logged_in = False
            self.got_user_join = False
            self.joined_channel = False

        async def on_ready(self):
            self.logged_in = True

        async def on_user_join(self, channel: Channel, user_login: str):
            assert channel.login == IRC_USERNAME == user_login
            self.got_user_join = True

        async def on_channel_join(self, channel: Channel):
            assert channel.login == channel.client_state.login == IRC_USERNAME
            assert channel.client_state.is_broadcaster
            self.joined_channel = True
            await self.stop()
    # valid one
    valid_bot = LClient(IRC_TOKEN, IRC_USERNAME)

    await valid_bot.start([IRC_USERNAME])  # will be finished in `on_channel_join()`
    assert valid_bot.logged_in
    assert valid_bot.got_user_join
    assert valid_bot.joined_channel


@pytest.mark.asyncio
async def test_read_websocket():
    # invalid logging
    bot = Client('token', 'login', should_restart=False)
    await bot._log_in_irc()
    irc_msgs = (
        IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags'),
        IRCMessage(':tmi.twitch.tv NOTICE * :Login authentication failed')
    )
    index = 0
    async for irc_msg in bot._read_websocket():
        assert irc_msg == irc_msgs[index]
        index += 1
        if index == len(irc_msgs):
            break
    # connection closed error
    with pytest.raises(websockets.ConnectionClosedError):
        await bot._websocket.close(3000)
        await bot._read_websocket().__anext__()
    # connection closed
    with pytest.raises(StopAsyncIteration):
        bot._websocket = await websockets.connect(IRC_URI)
        assert bot._websocket.open
        await bot._websocket.close()
        await bot._read_websocket().__anext__()
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
            break


@pytest.mark.asyncio
async def test_first_log_in_irc():
    bot = Client('token', 'login', should_restart=False)
    with pytest.raises(LoginFailed):
        await bot._first_log_in_irc()
    with pytest.raises(CapReqError):
        bot._websocket = await websockets.connect(IRC_URI)
        await bot._send('CAP REQ :ttv.tv/membership ttv.tv/commands ttv.tv/tags')  # !ttv.tv!
        await bot._first_log_in_irc()

    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login, should_restart=False)
            self.logined = False

        async def on_ready(self):
            self.logined = True

    valid_bot = LClient(IRC_TOKEN, IRC_USERNAME)

    await valid_bot._first_log_in_irc()
    await asyncio.sleep(0.01)  # on_ready is delayed (task created not called) here we let other tasks work
    assert valid_bot.logined


@pytest.mark.asyncio
async def test_restart():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.is_logged_in = False
            self.is_reconnected = False
            self.is_channel_joined = False
            self.is_channel_updated = False
            self.is_local_state_updated = False
            self.is_nameslist_updated = False

        async def on_ready(self):
            assert not self.is_logged_in
            assert self.is_running
            self.is_logged_in = True

        async def on_reconnect(self):
            self.is_reconnected = True

        async def on_channel_join(self, channel: Channel):
            assert not self.is_channel_joined
            assert channel.login == IRC_USERNAME
            assert channel.client_state.is_broadcaster
            self.is_channel_joined = True

        async def on_channel_update(self, before: Channel, after: Channel):
            assert before.login == after.login == IRC_USERNAME
            assert before.client_state.login == after.client_state.login == IRC_USERNAME
            self.is_channel_updated = True

        async def on_client_state_update(self, channel: Channel, before: LocalState, after: LocalState):
            assert channel.login == before.login == after.login == IRC_USERNAME
            assert before.is_broadcaster and after.is_broadcaster
            self.is_local_state_updated = True

        async def on_names_update(self, channel: Channel, before, after):
            assert channel.login == IRC_USERNAME
            assert IRC_USERNAME in before and IRC_USERNAME in after
            self.is_nameslist_updated = True

    valid_bot = LClient(IRC_TOKEN, IRC_USERNAME)
    valid_bot.loop.create_task(valid_bot.start([IRC_USERNAME]))
    await asyncio.sleep(2)  # let the task work

    await valid_bot.restart()
    assert not valid_bot.is_restarting
    await asyncio.sleep(2)
    assert valid_bot.is_logged_in
    assert valid_bot.is_channel_joined
    assert valid_bot.is_reconnected
    assert valid_bot.is_channel_updated
    assert valid_bot.is_local_state_updated
    assert valid_bot.is_nameslist_updated


async def handle_commands(client: Client, *irc_msgs: IRCMessage):
    for irc_msg in irc_msgs:
        await client._handle_command(irc_msg)


@pytest.mark.asyncio
async def test_handle_command():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.is_on_unknown_command_called = False
            
        async def on_message(self, message): pass  # just to make bot handle PRIVMSG
            
        async def on_unknown_command(self, irc_msg):
            assert irc_msg is CAP
            self.is_on_unknown_command_called = True

    # delay msg
    bot = LClient('token', 'login')
    await handle_commands(bot, MSG, CAP)
    await asyncio.sleep(0.001)
    assert bot._delayed_irc_msgs['target'] == [MSG]
    assert bot.is_on_unknown_command_called
    # also is being tested in test_handle_* tests


@pytest.mark.asyncio
async def test_handle_names_part():
    bot = Client('token', 'login')
    # set(update)
    await bot._handle_command(NP)
    assert bot._channels_accumulator.names['target'] == list(NAMES[:3])
    # update
    await bot._handle_command(NP2)
    assert bot._channels_accumulator.pop_names('target') == NAMES


@pytest.mark.asyncio
async def test_handle_names_end():
    bot = Client('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS)
    assert bot.get_channel('target').names == NAMES
    # also is being tested in `test_handle_names_update()`


@pytest.mark.asyncio
async def test_handle_names_update():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.is_names_updated = False

        async def on_names_update(self, channel: Channel, before: Tuple, after: Tuple):
            assert before == NAMES
            assert after == NAMES[3:]
            assert channel.login == 'target'
            self.is_names_updated = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, NP2, NE)
    assert bot.get_channel('target').names == NAMES[3:]
    await asyncio.sleep(0.001)
    assert bot.is_names_updated


@pytest.mark.asyncio
async def test_handle_roomstate():
    bot = Client('token', 'login')
    await bot._handle_command(RS)
    assert bot._channels_accumulator.channel_states['target'] is RS
    # also is being tested in `test_handle_channel_update()`


@pytest.mark.asyncio
async def test_handle_channel_update():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.is_channel_updated = False

        async def on_channel_update(self, before: Channel, after: Channel):
            assert before.login == after.login == 'target'
            assert not before.is_emote_only and after.is_emote_only
            self.is_channel_updated = True

    bot = LClient('token', 'login')
    _RS = RS.copy()
    _RS.tags.update({'emote-only': '1'})
    await handle_commands(bot, *CHANNEL_PARTS, _RS)
    assert bot.get_channel_by_login('target').is_emote_only
    await asyncio.sleep(0.001)
    assert bot.is_channel_updated


@pytest.mark.asyncio
async def test_handle_userstate():
    bot = Client('token', 'login')
    await handle_commands(bot, GS, US)
    assert bot._channels_accumulator.client_states['target'] == LocalState(US)


@pytest.mark.asyncio
async def test_handle_userstate_update():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.is_userstate_updated = False

        async def on_client_state_update(self, channel: Channel, before: LocalState, after: LocalState):
            assert channel.login == 'target'
            assert before.login == after.login == 'login'
            assert not before.is_broadcaster and after.is_broadcaster
            self.is_userstate_updated = True

    bot = LClient('token', 'login')
    _US = US.copy()
    _US.tags.update({'badges': 'broadcaster/1'})
    await handle_commands(bot, *CHANNEL_PARTS, _US)
    await asyncio.sleep(0.001)
    assert bot.is_userstate_updated
    

@pytest.mark.asyncio
async def test_handle_privmsg():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.did_handle_message = False

        async def on_message(self, msg: ChannelMessage):
            assert msg.channel.login == 'target'
            assert msg.content == 'content with a @mention :('
            assert msg.author.login == 'username' and msg.author.display_name == 'UserName'
            assert not msg.is_reply
            self.did_handle_message = True
    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, MSG)
    await asyncio.sleep(0.001)
    assert bot.did_handle_message


@pytest.mark.asyncio
async def test_handle_whisper():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.did_handle_whisper = False

        async def on_whisper(self, whisper: Whisper):
            assert whisper.author.login == 'username'
            assert whisper.content == 'content with a @mention :('
            assert not whisper.emote_only
            self.did_handle_whisper = True
    bot = LClient('token', 'login')
    await bot._handle_command(WP)
    await asyncio.sleep(0.001)
    assert bot.did_handle_whisper


@pytest.mark.asyncio
async def test_handle_join():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.did_join = False

        async def on_user_join(self, channel: Channel, login: str):
            assert channel.login == 'target'
            assert login == 'username'
            self.did_join = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, JN)
    await asyncio.sleep(0.001)
    assert bot.did_join


@pytest.mark.asyncio
async def test_handle_part():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.did_part = False

        async def on_user_part(self, channel: Channel, login: str):
            assert channel.login == 'target'
            assert login == 'username'
            self.did_part = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, PT)
    await asyncio.sleep(0.001)
    assert bot.did_part


@pytest.mark.asyncio
async def test_handle_notice():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_notice = False

        async def on_notice(self, event: OnNotice):
            assert event.message == 'You cannot whisper to yourself.'
            assert event.notice_id == 'whisper_invalid_self'
            assert event.channel.login == 'target'
            self.got_notice = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, NT)
    await asyncio.sleep(0.001)
    assert bot.got_notice
    # also is being tested in several next tests


@pytest.mark.asyncio
async def test_handle_channel_join_error():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_channel_join_error = False

        async def on_channel_join_error(self, event: OnChannelJoinError):
            assert event.message == 'This channel has been suspended.'
            assert event.reason == 'channel_suspended'
            assert event.channel_login == 'target'
            self.got_channel_join_error = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, NT_CS)
    await asyncio.sleep(0.001)
    assert bot.got_channel_join_error


@pytest.mark.asyncio
async def test_handle_send_message_error():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_send_message_error = False

        async def on_send_message_error(self, event: OnSendMessageError):
            assert event.message == 'This room is in followers-only mode. Follow target to join the community!'
            assert event.reason == 'followersonly_zero'
            assert event.channel.login == 'target'
            self.got_send_message_error = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, NT_FOZ)
    await asyncio.sleep(0.001)
    assert bot.got_send_message_error


@pytest.mark.asyncio
async def test_handle_mods():  # TODO: test no_mods
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_mods_update = False

        async def on_mods_update(self, channel, before, after):
            assert channel.login == 'target'
            assert before == MODS
            assert after == MODS2
            self.got_on_mods_update = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, RM2)
    await asyncio.sleep(0.001)
    assert bot.got_on_mods_update


@pytest.mark.asyncio
async def test_handle_vips():  # TODO: test no_vips
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_vips_update = False

        async def on_vips_update(self, channel, before, after):
            assert channel.login == 'target'
            assert before == VIPS
            assert after == VIPS2
            self.got_on_vips_update = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, VS2)
    await asyncio.sleep(0.001)
    assert bot.got_on_vips_update


@pytest.mark.asyncio
async def test_handle_cmds_available():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_commands_update = False

        async def on_commands_update(self, channel, before, after):
            assert channel.login == 'target'
            assert before == CMDS
            assert after == CMDS2
            self.got_on_commands_update = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, CA2)
    await asyncio.sleep(0.001)
    assert bot.got_on_commands_update


@pytest.mark.asyncio
async def test_handle_clearchat():
    """Is being tested in `test_handle_timeout`, `test_handle_ban` and `test_hanlde_clear_chat`"""


@pytest.mark.asyncio
async def test_handle_timeout():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_timeout = False

        async def on_user_timeout(self, event: OnUserTimeout):
            assert event.message_id == '1-2-3'
            assert event.user_id == '012345'
            assert event.user_login == 'username'
            assert event.duration == 600
            assert event.channel.login == 'target'
            self.got_on_timeout = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, CC_UT)
    await asyncio.sleep(0.001)
    assert bot.got_on_timeout


@pytest.mark.asyncio
async def test_handle_ban():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_ban = False

        async def on_user_ban(self, event: OnUserBan):
            assert event.message_id == '1-2-3'
            assert event.user_id == '012345'
            assert event.user_login == 'username'
            assert event.channel.login == 'target'
            self.got_on_ban = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, CC_UB)
    await asyncio.sleep(0.001)
    assert bot.got_on_ban


@pytest.mark.asyncio
async def test_hanlde_clear_chat():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_clear_chat = False

        async def on_clear_chat(self, event: OnClearChat):
            assert event.channel.login == 'target'
            assert event.timestamp == 1629011347771
            self.got_on_clear_chat = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, CC_CC)
    await asyncio.sleep(0.001)
    assert bot.got_on_clear_chat


@pytest.mark.asyncio
async def test_handle_clearmsg():
    class LClient(Client):
        def __init__(self, token: str, login: str):
            super().__init__(token, login)
            self.got_on_message_delete = False

        async def on_message_delete(self, event: OnMessageDelete):
            assert event.message_id == '1-2-3'
            assert event.user_login == 'username'
            assert event.content == "deleted message's content"
            assert event.channel.login == 'target'
            self.got_on_message_delete = True

    bot = LClient('token', 'login')
    await handle_commands(bot, *CHANNEL_PARTS, CM)
    await asyncio.sleep(0.001)
    assert bot.got_on_message_delete



