from ttv.irc import IRCMessage


CAP = IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
GS = IRCMessage('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 GLOBALUSERSTATE')
RS = IRCMessage('@emote-only=0;followers-only=-1;r9k=0;rituals=0;room-id=12345;slow=0;subs-only=0 ROOMSTATE #target')
US = IRCMessage('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 USERSTATE #target')
NP = IRCMessage('353 #target :username1 username2 username3')
NP2 = IRCMessage('353 #target :username4 username5 username6')
NE = IRCMessage('366 #target')
NAMES = tuple(['username1', 'username2', 'username3'] + ['username4', 'username5', 'username6'])
# mods
RM = IRCMessage(
    '@msg-id=room_mods NOTICE #target :The moderators of this channel are: mod_login1, mod_login2, mod_login3'
)
RM2 = IRCMessage(
    '@msg-id=room_mods NOTICE #target :The moderators of this channel are: mod_login1, mod_login2, new_mod_login'
)
NRM = IRCMessage('@msg-id=no_mods :tmi.twitch.tv NOTICE #rows_ss :There are no moderators of this channel.')
MODS = ('mod_login1', 'mod_login2', 'mod_login3')
MODS2 = ('mod_login1', 'mod_login2', 'new_mod_login')
# vips
VS = IRCMessage(
    '@msg-id=vips_success NOTICE #target :The VIPs of this channel are: vip_login1, vip_login2, vip_login3.'
)
VS2 = IRCMessage(
    '@msg-id=vips_success NOTICE #target :The VIPs of this channel are: vip_login1, vip_login2, new_vip_login.'
)
NVS = IRCMessage('@msg-id=no_vips :tmi.twitch.tv NOTICE #target :This channel does not have any VIPs.')
VIPS = ('vip_login1', 'vip_login2', 'vip_login3')
VIPS2 = ('vip_login1', 'vip_login2', 'new_vip_login')
# commands
CA = IRCMessage(
    '@msg-id=cmds_available NOTICE #target :Commands available to you in this room (use /help <command> for details): '
    '/cmd1 /cmd2 /cmd3 More help: https://help.twitch.tv/s/article/chat-commands'
)
CA2 = IRCMessage(
    '@msg-id=cmds_available NOTICE #target :Commands available to you in this room (use /help <command> for details): '
    '/cmd1 /cmd2 /new_cmd More help: https://help.twitch.tv/s/article/chat-commands'
)
CMDS = ('/cmd1', '/cmd2', '/cmd3')
CMDS2 = ('/cmd1', '/cmd2', '/new_cmd')
# all channel_parts
CHANNEL_PARTS = (GS, RS, US, NP, NP2, NE, RM, VS, CA)
MSG = IRCMessage('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                 'PRIVMSG #target :content with a @mention :(')
WP = IRCMessage('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                'WHISPER target :content with a @mention :(')
JN = IRCMessage(':username!username@username.tmi.twitch.tv JOIN #target')
PT = IRCMessage(':username!username@username.tmi.twitch.tv PART #target')
NT = IRCMessage('@msg-id=whisper_invalid_self NOTICE #target :You cannot whisper to yourself.')
NT_CS = IRCMessage('@msg-id=msg_channel_suspended NOTICE #target :This channel has been suspended.')
NT_FOZ = IRCMessage('@msg-id=msg_followersonly_zero NOTICE #target :'
                    'This room is in followers-only mode. Follow target to join the community!')
