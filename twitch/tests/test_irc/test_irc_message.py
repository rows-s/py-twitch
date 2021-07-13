from twitch.irc import IRCMessage


def test_irc_message():
    # a real exapmle
    raw_irc_message = '@badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type= :fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv PRIVMSG #axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    irc_message = IRCMessage(raw_irc_message)
    irc_message_raw_tags = 'badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type='
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
    assert irc_message.raw_tags == irc_message_raw_tags
    assert irc_message.tags == irc_message_tags
    assert irc_message.prefix == 'fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv'
    assert irc_message.servername is None
    assert irc_message.nickname == 'fernandx_z'
    assert irc_message.user == 'fernandx_z'
    assert irc_message.host == 'fernandx_z.tmi.twitch.tv'
    assert irc_message.command == 'PRIVMSG'
    assert irc_message.raw_params == '#axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    assert irc_message.params == ('#axozer', '@MaYidRaMaS PERO JAJSJAJSJASJASJA')
    assert irc_message.middles == ('#axozer',)
    assert irc_message.trailing == irc_message.content == '@MaYidRaMaS PERO JAJSJAJSJASJASJA'


def test_parse_raw_irc_message():
    # command
    irc_message = IRCMessage('COMMAND')
    assert irc_message.raw_tags is None
    assert irc_message.prefix is None
    assert irc_message.command == 'COMMAND'
    assert irc_message.raw_params is None
    # command, params
    irc_message = IRCMessage('COMMAND #channel :trailing')
    assert irc_message.raw_tags is None
    assert irc_message.prefix is None
    assert irc_message.command == 'COMMAND'
    assert irc_message.raw_params == '#channel :trailing'
    # prefix, command
    irc_message = IRCMessage(':nickname!user@host COMMAND')
    assert irc_message.raw_tags is None
    assert irc_message.prefix == 'nickname!user@host'
    assert irc_message.command == 'COMMAND'
    assert irc_message.raw_params is None
    # tags, command
    irc_message = IRCMessage('@no-value-tag;key=value COMMAND')
    assert irc_message.raw_tags == 'no-value-tag;key=value'
    assert irc_message.prefix is None
    assert irc_message.command == 'COMMAND'
    assert irc_message.raw_params is None
    # tags, prefix, command
    irc_message = IRCMessage('@no-value-tag;key=value :nickname!user@host COMMAND')
    assert irc_message.raw_tags == 'no-value-tag;key=value'
    assert irc_message.prefix == 'nickname!user@host'
    assert irc_message.command == 'COMMAND'
    assert irc_message.raw_params is None


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
    # midle
    irc_message = IRCMessage('COMMAND middle')
    assert irc_message.params == ('middle',)
    assert irc_message.middles == ('middle',)
    assert irc_message.trailing is None
    # middle, trailing (':')
    irc_message = IRCMessage('COMMAND middle :trailing')
    assert irc_message.params == ('middle', 'trailing')
    assert irc_message.middles == ('middle',)
    assert irc_message.trailing == 'trailing'
    # middle, trailing (no ':')
    irc_message = IRCMessage('COMMAND ' + 'middle '*14 + 'trailing')
    assert irc_message.params == ('middle',) * 14 + ('trailing',)
    assert irc_message.middles == ('middle',) * 14
    assert irc_message.trailing == 'trailing'
    # trailing
    irc_message = IRCMessage('COMMAND :trailing')
    assert irc_message.params == ('trailing',)
    assert irc_message.middles == ()
    assert irc_message.trailing == 'trailing'
    # None
    irc_message = IRCMessage('COMMAND')
    assert irc_message.params == ()
    assert irc_message.middles == ()
    assert irc_message.trailing is None


def test_eq():
    assert IRCMessage('COMMAND') == IRCMessage('COMMAND')
    assert IRCMessage('COMMAND') != IRCMessage('ERROR')


def test_contains():
    assert 'COMMAND' in IRCMessage('COMMAND')
    assert 'COM' in IRCMessage('COMMAND')
    assert 'MMA' in IRCMessage('COMMAND')
    assert 'AND' in IRCMessage('COMMAND')
    assert 'A' not in IRCMessage('ERROR')


def test_str_repr():
    assert str(IRCMessage('COMMAND')) == 'COMMAND'
    assert repr(IRCMessage('COMMAND')) == 'COMMAND'

