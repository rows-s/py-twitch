from ttv.irc import TwitchIRCMsg


CAP = TwitchIRCMsg(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
GS = TwitchIRCMsg('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 GLOBALUSERSTATE')
RS = TwitchIRCMsg('@emote-only=0;followers-only=-1;r9k=0;rituals=0;room-id=12345;slow=0;subs-only=0 ROOMSTATE #target')
US = TwitchIRCMsg('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 USERSTATE #target')
NP = TwitchIRCMsg('353 #target :username1 username2 username3')
NP2 = TwitchIRCMsg('353 #target :username4 username5 username6')
NE = TwitchIRCMsg('366 #target')
NAMES = tuple(['username1', 'username2', 'username3'] + ['username4', 'username5', 'username6'])
# mods
RM = TwitchIRCMsg(
    '@msg-id=room_mods NOTICE #target :The moderators of this channel are: mod_login1, mod_login2, mod_login3'
)
RM2 = TwitchIRCMsg(
    '@msg-id=room_mods NOTICE #target :The moderators of this channel are: mod_login1, mod_login2, new_mod_login'
)
NRM = TwitchIRCMsg('@msg-id=no_mods :tmi.twitch.tv NOTICE #rows_ss :There are no moderators of this channel.')
MODS = ('mod_login1', 'mod_login2', 'mod_login3')
MODS2 = ('mod_login1', 'mod_login2', 'new_mod_login')
# vips
VS = TwitchIRCMsg(
    '@msg-id=vips_success NOTICE #target :The VIPs of this channel are: vip_login1, vip_login2, vip_login3.'
)
VS2 = TwitchIRCMsg(
    '@msg-id=vips_success NOTICE #target :The VIPs of this channel are: vip_login1, vip_login2, new_vip_login.'
)
NVS = TwitchIRCMsg('@msg-id=no_vips :tmi.twitch.tv NOTICE #target :This channel does not have any VIPs.')
VIPS = ('vip_login1', 'vip_login2', 'vip_login3')
VIPS2 = ('vip_login1', 'vip_login2', 'new_vip_login')
# commands
CA = TwitchIRCMsg(
    '@msg-id=cmds_available NOTICE #target :Commands available to you in this room (use /help <command> for details): '
    '/cmd1 /cmd2 /cmd3 More help: https://help.twitch.tv/s/article/chat-commands'
)
CA2 = TwitchIRCMsg(
    '@msg-id=cmds_available NOTICE #target :Commands available to you in this room (use /help <command> for details): '
    '/cmd1 /cmd2 /new_cmd More help: https://help.twitch.tv/s/article/chat-commands'
)
CMDS = ('/cmd1', '/cmd2', '/cmd3')
CMDS2 = ('/cmd1', '/cmd2', '/new_cmd')
# all channel_parts
CHANNEL_PARTS = (GS, RS, US, NP, NP2, NE, RM, VS, CA)
MSG = TwitchIRCMsg('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                 'PRIVMSG #target :content with a @mention :(')
WP = TwitchIRCMsg('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                'WHISPER target :content with a @mention :(')
JN = TwitchIRCMsg(':username!username@username.tmi.twitch.tv JOIN #target')
PT = TwitchIRCMsg(':username!username@username.tmi.twitch.tv PART #target')
NT = TwitchIRCMsg('@msg-id=whisper_invalid_self NOTICE #target :You cannot whisper to yourself.')
NT_CS = TwitchIRCMsg('@msg-id=msg_channel_suspended NOTICE #target :This channel has been suspended.')
NT_FOZ = TwitchIRCMsg('@msg-id=msg_followersonly_zero NOTICE #target :'
                    'This room is in followers-only mode. Follow target to join the community!')

CC_UT = TwitchIRCMsg('@ban-duration=600;target-user-id=012345;target-msg-id=1-2-3 CLEARCHAT #target :username')
CC_UB = TwitchIRCMsg('@target-user-id=012345;target-msg-id=1-2-3 CLEARCHAT #target :username')
CC_CC = TwitchIRCMsg('@tmi-sent-ts=1629011347771 CLEARCHAT #target')
CM = TwitchIRCMsg("@target-msg-id=1-2-3;login=username CLEARMSG #target :deleted message's content")
