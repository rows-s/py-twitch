import asyncio
import os
from typing import Tuple

import pytest

from tests.test_irc.irc_msgs import *
from ttv.irc import Client, Channel, LocalState, ChannelMessage, Whisper
from ttv.irc.events import *
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
    with pytest.raises(ChannelNotAccumulated):
        bot._get_prepared_channel('')


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


async def handle_commands(client: Client, *irc_msgs: TwitchIRCMsg):
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
            assert irc_msg is CAPS
            self.is_on_unknown_command_called = True

    # delay msg
    bot = LClient('token', 'login')
    await handle_commands(bot, PRIVMSG, CAPS)
    await asyncio.sleep(0.001)
    assert bot._delayed_irc_msgs['target'] == [PRIVMSG]
    assert bot.is_on_unknown_command_called
    # also is being tested in test_handle_* tests


@pytest.mark.asyncio
async def test_handle_names_part():
    bot = Client('token', 'login')
    # set(update)
    await handle_commands(bot, NAMES_PART, NAMES_END)
    assert (await bot._chnls_accum.get_parts('target')).names == NAMES[:3]
    # update
    await handle_commands(bot, NAMES_PART, NAMES_PART2, NAMES_END)
    assert (await bot._chnls_accum.get_parts('target')).names == NAMES


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
    await handle_commands(bot, *CHANNEL_PARTS, NAMES_PART2, NAMES_END)
    assert bot.get_channel('target').names == NAMES[3:]
    await asyncio.sleep(0.001)
    assert bot.is_names_updated


@pytest.mark.asyncio
async def test_handle_roomstate():
    bot = Client('token', 'login')
    await bot._handle_command(ROOMSTATE)
    assert (await bot._chnls_accum.get_parts('target')).raw_channel_state == ROOMSTATE
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
    _RS = ROOMSTATE.copy()
    _RS.update({'emote-only': '1'})
    await handle_commands(bot, *CHANNEL_PARTS, _RS)
    assert bot.get_channel_by_login('target').is_emote_only
    await asyncio.sleep(0.001)
    assert bot.is_channel_updated


@pytest.mark.asyncio
async def test_handle_userstate():
    bot = Client('token', 'login')
    await handle_commands(bot, GLOBALSTATE, USERSTATE)
    assert (await bot._chnls_accum.get_parts('target')).client_state == LocalState(USERSTATE)


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
    _US = USERSTATE.copy()
    _US.update({'badges': 'broadcaster/1'})
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
    await handle_commands(bot, *CHANNEL_PARTS, PRIVMSG)
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
    await bot._handle_command(WHISPER)
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
    await handle_commands(bot, *CHANNEL_PARTS, JOIN)
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
    await handle_commands(bot, *CHANNEL_PARTS, PART)
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
    await handle_commands(bot, *CHANNEL_PARTS, NT_WHISPER_INVALID_SELF)
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
    await handle_commands(bot, *CHANNEL_PARTS, NT_CHNL_SUSPENDED)
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
    await handle_commands(bot, *CHANNEL_PARTS, NT_FLWONLY_0)
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
    await handle_commands(bot, *CHANNEL_PARTS, ROOM_MODS2)
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
    await handle_commands(bot, *CHANNEL_PARTS, ROOM_VIPS2)
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
    await handle_commands(bot, *CHANNEL_PARTS, ROOM_CMDS2)
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
    await handle_commands(bot, *CHANNEL_PARTS, CLEARCHAT_TIMEOUT)
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
    await handle_commands(bot, *CHANNEL_PARTS, CLEARCHAT_BAN)
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
    await handle_commands(bot, *CHANNEL_PARTS, CLEARCHAT)
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
    await handle_commands(bot, *CHANNEL_PARTS, CLEARMSG)
    await asyncio.sleep(0.001)
    assert bot.got_on_message_delete



