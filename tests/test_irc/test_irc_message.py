from ttv.irc import IRCMessage


def test_irc_msg():
    # a real example
    raw_irc_msg = '@badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type= :fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv PRIVMSG #axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    irc_msg = IRCMessage(raw_irc_msg)
    irc_msg_tags = {
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
    assert irc_msg.tags == irc_msg_tags
    assert irc_msg.servername is None
    assert irc_msg.nickname == 'fernandx_z'
    assert irc_msg.user == 'fernandx_z'
    assert irc_msg.host == 'fernandx_z.tmi.twitch.tv'
    assert irc_msg.command == 'PRIVMSG'
    assert irc_msg.middles == ('#axozer',)
    assert irc_msg.channel == 'axozer'
    assert irc_msg.trailing == irc_msg.trailing == '@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    assert str(irc_msg) == raw_irc_msg


def test_parse_raw_tags():
    irc_msg = IRCMessage(r'@no-value-tag;key=value;key2=escaped\svalue\\\: COMMAND')
    assert irc_msg.tags == {'no-value-tag': None, 'key': 'value', 'key2': r'escaped value\;'}
    # None
    irc_msg = IRCMessage('COMMAND')
    assert irc_msg.tags == {}


def test_parse_prefix():
    # servername
    irc_msg = IRCMessage(r':server.name.tv COMMAND')
    assert irc_msg.servername == 'server.name.tv'
    assert irc_msg.nickname is None
    assert irc_msg.user is None
    assert irc_msg.host is None
    # full
    irc_msg = IRCMessage(r':nickname!user@host COMMAND')
    assert irc_msg.servername is None
    assert irc_msg.nickname == 'nickname'
    assert irc_msg.user == 'user'
    assert irc_msg.host == 'host'
    # no user
    irc_msg = IRCMessage(r':nickname@host COMMAND')
    assert irc_msg.servername is None
    assert irc_msg.nickname == 'nickname'
    assert irc_msg.user is None
    assert irc_msg.host == 'host'
    # no user, no host
    irc_msg = IRCMessage(r':nickname COMMAND')
    assert irc_msg.servername is None
    assert irc_msg.nickname == 'nickname'
    assert irc_msg.user is None
    assert irc_msg.host is None
    # None
    irc_msg = IRCMessage('COMMAND')
    assert irc_msg.servername is None
    assert irc_msg.nickname is None
    assert irc_msg.user is None
    assert irc_msg.host is None


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
    irc_msg = IRCMessage('@key=value;no-value-tag :username COMMAND')
    new_msg = IRCMessage('@key=value;no-value-tag :username COMMAND')
    assert irc_msg == new_msg
    # different positions tags
    irc_msg = IRCMessage('@key=value;no-value-tag :username COMMAND')
    new_msg = IRCMessage('@no-value-tag;key=value :username COMMAND')
    assert irc_msg == new_msg
    # same positions middles
    irc_msg = IRCMessage('@key=value;no-value-tag :username COMMAND param #target')
    new_msg = IRCMessage('@no-value-tag;key=value :username COMMAND param #target')
    assert irc_msg == new_msg
    # different positions middles
    irc_msg = IRCMessage('@key=value;no-value-tag :username COMMAND param #target :trai :ling')
    new_msg = IRCMessage('@no-value-tag;key=value :username COMMAND #target param :trai :ling')
    assert irc_msg == new_msg
    # others
    assert IRCMessage('COMMAND') == IRCMessage('COMMAND')
    assert IRCMessage('COMMAND') != IRCMessage('ERROR')


def test_str_repr():
    assert str(IRCMessage('COMMAND')) == 'COMMAND'
    assert repr(IRCMessage('COMMAND')) == 'COMMAND'
    raw_irc_msg = '@key=value;no-value-tag :username COMMAND param #target :trai :ling'
    assert str(IRCMessage(raw_irc_msg)) == raw_irc_msg
    raw_irc_msg = '@badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type= :fernandx_z!fernandx_z@fernandx_z.tmi.twitch.tv PRIVMSG #axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
    assert str(IRCMessage(raw_irc_msg)) == raw_irc_msg
