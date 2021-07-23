from ttv.irc import IRCMessage


def test_irc_message():
    # a real example
    raw_irc_message = '@badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type= :fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv PRIVMSG #axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    irc_message = IRCMessage(raw_irc_message)
    irc_message_tags = {
        'badge-info': 'subscriber/1', 'badges': 'subscriber/0',
        'client-nonce': '3f58e4f3107d580b8a29626738823a5c',
        'color': '#FF69B4',
        'display-name': 'fernandx_z',
        'emotes': '',
        'flags': '',
        'id': 'aa3b5987-1929-414c-bc55-10f9e6c1723e',
        'mod': '0',
        'reply-parent-display-name': 'MaYidRaMaS',
        'reply-parent-msg-body': 'axozerTem ato axozerPium axozerPium_HF',
        'reply-parent-msg-id': '2f06b2b8-d33d-4e65-a0c4-82d1894c7b63',
        'reply-parent-user-id': '612074199',
        'reply-parent-user-login': 'mayidramas',
        'room-id': '133528221',
        'subscriber': '1',
        'tmi-sent-ts': '1622471612333',
        'turbo': '0',
        'user-id': '602696060',
        'user-type': ''
    }
    assert irc_message.tags == irc_message_tags
    assert irc_message.servername is None
    assert irc_message.nickname == 'fernandx_z'
    assert irc_message.user == 'fernandx_z'
    assert irc_message.host == 'fernandx_z.tmi.twitch.tv'
    assert irc_message.command == 'PRIVMSG'
    assert irc_message.middles == ('#axozer',)
    assert irc_message.channel == 'axozer'
    assert irc_message.trailing == irc_message.content == '@MaYidRaMaS PERO JAJSJAJSJASJASJA'


def test_parse_raw_irc_message():
    # command
    assert IRCMessage._parse_raw_irc_msg('COMMAND') == (None, None, 'COMMAND', None)
    # command, params
    assert IRCMessage._parse_raw_irc_msg(
        'COMMAND #channel :trailing'
    ) == (None, None, 'COMMAND', '#channel :trailing')
    # prefix, command
    assert IRCMessage._parse_raw_irc_msg(
        ':nickname!user@host COMMAND'
    ) == (None, 'nickname!user@host', 'COMMAND', None)
    # tags, command
    assert IRCMessage._parse_raw_irc_msg(
        '@no-value-tag;key=value COMMAND'
    ) == ('no-value-tag;key=value', None, 'COMMAND', None)
    # tags, prefix, command
    assert IRCMessage._parse_raw_irc_msg(
        '@no-value-tag;key=value :nickname!user@host COMMAND'
    ) == ('no-value-tag;key=value', 'nickname!user@host', 'COMMAND', None)
    # tags, prefix, command, params
    assert IRCMessage._parse_raw_irc_msg(
        '@no-value-tag;key=value :nickname!user@host COMMAND middle #target :trailing'
    ) == ('no-value-tag;key=value', 'nickname!user@host', 'COMMAND', 'middle #target :trailing')


def test_parse_raw_tags():
    irc_message = IRCMessage(r'@no-value-tag;key=value;key2=escaped\svalue\\\:;fix-slash=1\ COMMAND')
    assert irc_message.tags == {'no-value-tag': None, 'key': 'value', 'key2': r'escaped value\;', 'fix-slash': '1'}
    # None
    irc_message = IRCMessage('COMMAND')
    assert irc_message.tags == {}


def test_parse_prefix():
    # servername
    irc_message = IRCMessage(r':server.name.tv COMMAND')
    assert irc_message.servername == 'server.name.tv'
    assert irc_message.nickname is None
    assert irc_message.user is None
    assert irc_message.host is None
    # full
    irc_message = IRCMessage(r':nickname!user@host COMMAND')
    assert irc_message.servername is None
    assert irc_message.nickname == 'nickname'
    assert irc_message.user == 'user'
    assert irc_message.host == 'host'
    # no user
    irc_message = IRCMessage(r':nickname@host COMMAND')
    assert irc_message.servername is None
    assert irc_message.nickname == 'nickname'
    assert irc_message.user is None
    assert irc_message.host == 'host'
    # no user, no host
    irc_message = IRCMessage(r':nickname COMMAND')
    assert irc_message.servername is None
    assert irc_message.nickname == 'nickname'
    assert irc_message.user is None
    assert irc_message.host is None
    # None
    irc_message = IRCMessage('COMMAND')
    assert irc_message.servername is None
    assert irc_message.nickname is None
    assert irc_message.user is None
    assert irc_message.host is None


def test_parse_raw_params():
    # middle
    irc_msg = IRCMessage('COMMAND middle')
    assert irc_msg.middles == ('middle',)
    assert irc_msg.trailing is None
    # middle, trailing (':')
    irc_msg = IRCMessage('COMMAND middle :trailing')
    assert irc_msg.middles == ('middle',)
    assert irc_msg.trailing == 'trailing'
    # same and trailing contains separators
    irc_msg = IRCMessage('COMMAND middle :trai :ling')
    assert irc_msg.middles == ('middle',)
    assert irc_msg.trailing == 'trai :ling'
    # middle, trailing (no ':')
    irc_msg = IRCMessage('COMMAND ' + 'middle '*14 + 'trailing')
    assert irc_msg.middles == ('middle',) * 14
    assert irc_msg.trailing == 'trailing'
    # same and trailing contains separators
    irc_msg = IRCMessage('COMMAND ' + 'middle '*14 + 'trai :ling')
    assert irc_msg.middles == ('middle',) * 14
    assert irc_msg.trailing == 'trai :ling'
    # trailing
    irc_msg = IRCMessage('COMMAND :trailing')
    assert irc_msg.middles == ()
    assert irc_msg.trailing == 'trailing'
    # None
    irc_msg = IRCMessage('COMMAND')
    assert irc_msg.middles == ()
    assert irc_msg.trailing is None
    # channel
    irc_msg = IRCMessage('COMMAND #channel_login middle last')
    assert irc_msg.channel == 'channel_login'
    irc_msg = IRCMessage('COMMAND first #channel_login last')
    assert irc_msg.channel == 'channel_login'
    irc_msg = IRCMessage('COMMAND first middle #channel_login')
    assert irc_msg.channel == 'channel_login'
    irc_msg = IRCMessage('COMMAND first middle #channel_login :trai :ling')
    assert irc_msg.channel == 'channel_login'
    irc_msg = IRCMessage('COMMAND first middle channel_login :trai :ling')
    assert irc_msg.channel is None


def test_join_tags():
    irc_msg = IRCMessage.create_empty()
    irc_msg.tags = {'one-tag': 'one-value'}
    assert irc_msg._join_tags() == 'one-tag=one-value'
    irc_msg.tags = {'one-no-tag-value': None}
    assert irc_msg._join_tags() == 'one-no-tag-value'
    irc_msg.tags = {'key': 'value', 'no-value-tag': None, 'key2': 'value2'}
    assert irc_msg._join_tags() == 'key=value;no-value-tag;key2=value2'


def test_eq():
    # same positions tags
    irc_msg = IRCMessage('@key-value;no-value-tag :username COMMAND')
    new_msg = IRCMessage('@key-value;no-value-tag :username COMMAND')
    assert irc_msg == new_msg
    # different positions tags
    irc_msg = IRCMessage('@key-value;no-value-tag :username COMMAND')
    new_msg = IRCMessage('@no-value-tag;key-value :username COMMAND')
    assert irc_msg == new_msg
    # same positions middles
    irc_msg = IRCMessage('@key-value;no-value-tag :username COMMAND param #target')
    new_msg = IRCMessage('@no-value-tag;key-value :username COMMAND param #target')
    assert irc_msg == new_msg
    # different positions middles
    irc_msg = IRCMessage('@key-value;no-value-tag :username COMMAND param #target :trai :ling')
    new_msg = IRCMessage('@no-value-tag;key-value :username COMMAND #target param :trai :ling')
    assert irc_msg == new_msg
    # others
    assert IRCMessage('COMMAND') == IRCMessage('COMMAND')
    assert IRCMessage('COMMAND') != IRCMessage('ERROR')


def test_str_repr():
    assert str(IRCMessage('COMMAND')) == 'COMMAND'
    assert repr(IRCMessage('COMMAND')) == 'COMMAND'
    raw_irc_msg = '@key-value;no-value-tag :username COMMAND param #target :trai :ling'
    assert str(IRCMessage(raw_irc_msg)) == raw_irc_msg
    raw_irc_msg = '@badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type= :fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv PRIVMSG #axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    assert str(IRCMessage(raw_irc_msg)) == raw_irc_msg
