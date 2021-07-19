from ttv.irc import IRCMessage


def test_irc_message():
    # a real exapmle
    raw_irc_message = '@badge-info=subscriber/1;badges=subscriber/0;client-nonce=3f58e4f3107d580b8a29626738823a5c;color=#FF69B4;display-name=fernandx_z;emotes=;flags=;id=aa3b5987-1929-414c-bc55-10f9e6c1723e;mod=0;reply-parent-display-name=MaYidRaMaS;reply-parent-msg-body=axozerTem\\sato\\saxozerPium\\saxozerPium_HF;reply-parent-msg-id=2f06b2b8-d33d-4e65-a0c4-82d1894c7b63;reply-parent-user-id=612074199;reply-parent-user-login=mayidramas;room-id=133528221;subscriber=1;tmi-sent-ts=1622471612333;turbo=0;user-id=602696060;user-type= :fernandx_z!fernandx_z@fernandx_z.tmi.ttv.tv PRIVMSG #axozer :@MaYidRaMaS PERO JAJSJAJSJASJASJA'
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
    assert irc_message.prefix == 'fernandx_z!fernandx_z@fernandx_z.tmi.ttv.tv'
    assert irc_message.servername is None
    assert irc_message.nickname == 'fernandx_z'
    assert irc_message.user == 'fernandx_z'
    assert irc_message.host == 'fernandx_z.tmi.ttv.tv'
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
    # same and trailing contains separators
    irc_message = IRCMessage('COMMAND middle :trai :ling')
    assert irc_message.params == ('middle', 'trai :ling')
    assert irc_message.middles == ('middle',)
    assert irc_message.trailing == 'trai :ling'
    # middle, trailing (no ':')
    irc_message = IRCMessage('COMMAND ' + 'middle '*14 + 'trailing')
    assert irc_message.params == ('middle',) * 14 + ('trailing',)
    assert irc_message.middles == ('middle',) * 14
    assert irc_message.trailing == 'trailing'
    # same and trailing contains separators
    irc_message = IRCMessage('COMMAND ' + 'middle '*14 + 'trai :ling')
    assert irc_message.params == ('middle',) * 14 + ('trai :ling',)
    assert irc_message.middles == ('middle',) * 14
    assert irc_message.trailing == 'trai :ling'
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


def test_update_tags():
    def assert_tags(irc_msg1, irc_msg2):
        assert irc_msg1 == irc_msg2
        assert irc_msg1.raw_tags == irc_msg2.raw_tags
        assert irc_msg1.tags == irc_msg2.tags
    # add to empty
    irc_msg = IRCMessage(r'COMMAND')
    new_msg = IRCMessage(r'@no-value-tag;key=value COMMAND')
    irc_msg.update_tags({'no-value-tag': None, 'key': 'value'})
    assert_tags(irc_msg, new_msg)
    # add to not empty
    irc_msg = IRCMessage(r'@key2=value2 COMMAND')
    new_msg = IRCMessage(r'@key2=value2;no-value-tag;key=value COMMAND')
    irc_msg.update_tags({'no-value-tag': None, 'key': 'value'})
    assert_tags(irc_msg, new_msg)
    # add with update value
    irc_msg = IRCMessage(r'@key2=value2;no-value-tag=some-value COMMAND')
    new_msg = IRCMessage(r'@key2=value2;no-value-tag;key=value COMMAND')
    irc_msg.update_tags({'no-value-tag': None, 'key': 'value'})
    assert_tags(irc_msg, new_msg)
    # add empty
    irc_msg = IRCMessage(r'@key2=value2;no-value-tag;key=value COMMAND')
    new_msg = IRCMessage(r'@key2=value2;no-value-tag;key=value COMMAND')
    irc_msg.update_tags({})
    assert_tags(irc_msg, new_msg)
    # value that requires escaping
    irc_msg = IRCMessage(r'@key2=value2;no-value-tag;key=value COMMAND')
    new_msg = IRCMessage(r'@key2=value2;no-value-tag;key=val\:ue\s\\\\ COMMAND')
    irc_msg.update_tags({'key': r'val;ue \\'})
    assert_tags(irc_msg, new_msg)


def test_pop_tag():
    def assert_tags(irc_msg1, irc_msg2):
        assert irc_msg1 == irc_msg2
        assert irc_msg1.raw_tags == irc_msg2.raw_tags
        assert irc_msg1.tags == irc_msg2.tags
    # pop one tag from multiple tags
    irc_msg = IRCMessage(r'@no-value-tag;key=value;key2=escaped\svalue\\\: COMMAND')
    new_msg = IRCMessage(r'@no-value-tag;key2=escaped\svalue\\\: COMMAND')
    assert irc_msg.pop_tag('key') == 'value'
    assert_tags(irc_msg, new_msg)
    # pop one tag from one-tag tags
    irc_msg = IRCMessage(r'@beginig-key=beginig-value COMMAND')
    new_msg = IRCMessage(r'COMMAND')
    assert irc_msg.pop_tag('beginig-key') == 'beginig-value'
    assert_tags(irc_msg, new_msg)
    # pop from begining
    irc_msg = IRCMessage(r'@beginig-key=beginig-value;middle-key=middle-value;end-key=end-value COMMAND')
    new_msg = IRCMessage(r'@middle-key=middle-value;end-key=end-value COMMAND')
    assert irc_msg.pop_tag('beginig-key') == 'beginig-value'
    assert_tags(irc_msg, new_msg)
    # pop from middle
    irc_msg = IRCMessage(r'@beginig-key=beginig-value;middle-key=middle-value;end-key=end-value COMMAND')
    new_msg = IRCMessage(r'@beginig-key=beginig-value;end-key=end-value COMMAND')
    assert irc_msg.pop_tag('middle-key') == 'middle-value'
    assert_tags(irc_msg, new_msg)
    # pop from end
    irc_msg = IRCMessage(r'@beginig-key=beginig-value;middle-key=middle-value;end-key=end-value COMMAND')
    new_msg = IRCMessage(r'@beginig-key=beginig-value;middle-key=middle-value COMMAND')
    assert irc_msg.pop_tag('end-key') == 'end-value'
    assert_tags(irc_msg, new_msg)
    # pop no-value-tag
    irc_msg = IRCMessage(r'@no-value-tag :tmi.twitch.tv COMMAND')
    new_msg = IRCMessage(r':tmi.twitch.tv COMMAND')
    assert irc_msg.pop_tag('no-value-tag') is None
    assert_tags(irc_msg, new_msg)
    # pop value-tag
    irc_msg = IRCMessage(r'@value-tag=value :tmi.twitch.tv COMMAND')
    new_msg = IRCMessage(r':tmi.twitch.tv COMMAND')
    assert irc_msg.pop_tag('value-tag') == 'value'
    # escaped value
    irc_msg = IRCMessage(r'@escaped-tag=val\:ue\s\\;no-value-tag :tmi.twitch.tv COMMAND')
    new_msg = IRCMessage(r'@escaped-tag=val\:ue\s\\ :tmi.twitch.tv COMMAND')
    assert irc_msg.pop_tag('no-value-tag') is None
    assert_tags(irc_msg, new_msg)
    assert irc_msg.pop_tag('escaped-tag') == 'val;ue \\'
    new_msg = IRCMessage(r':tmi.twitch.tv COMMAND')
    assert_tags(irc_msg, new_msg)


def test_eq():
    assert IRCMessage('COMMAND') == IRCMessage('COMMAND')
    assert IRCMessage('COMMAND') != IRCMessage('ERROR')


def test_contains():
    assert 'COMMAND' in IRCMessage('COMMAND')
    assert IRCMessage('COMMAND') in IRCMessage('COMMAND')
    assert 'COM' in IRCMessage('COMMAND')
    assert 'MMA' in IRCMessage('COMMAND')
    assert 'AND' in IRCMessage('COMMAND')
    assert 'A' not in IRCMessage('ERROR')


def test_str_repr():
    assert str(IRCMessage('COMMAND')) == 'COMMAND'
    assert repr(IRCMessage('COMMAND')) == 'COMMAND'

