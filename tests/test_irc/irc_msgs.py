from ttv.irc import TwitchIRCMsg


CAPS = TwitchIRCMsg(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
GLOBALSTATE = TwitchIRCMsg('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 GLOBALUSERSTATE')
ROOMSTATE = TwitchIRCMsg('@emote-only=0;followers-only=-1;r9k=0;rituals=0;room-id=12345;slow=0;subs-only=0 ROOMSTATE #target')
USERSTATE = TwitchIRCMsg('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 USERSTATE #target')
NAMES_PART = TwitchIRCMsg('353 #target :username1 username2 username3')
NAMES_PART2 = TwitchIRCMsg('353 #target :username4 username5 username6')
NAMES_END = TwitchIRCMsg('366 #target')
NAMES = tuple(['username1', 'username2', 'username3'] + ['username4', 'username5', 'username6'])
# mods
ROOM_MODS = TwitchIRCMsg(
    '@msg-id=room_mods NOTICE #target :The moderators of this channel are: mod_login1, mod_login2, mod_login3'
)
ROOM_MODS2 = TwitchIRCMsg(
    '@msg-id=room_mods NOTICE #target :The moderators of this channel are: mod_login1, mod_login2, new_mod_login'
)
NO_MODS = TwitchIRCMsg('@msg-id=no_mods :tmi.twitch.tv NOTICE #target :There are no moderators of this channel.')
MODS = ('mod_login1', 'mod_login2', 'mod_login3')
MODS2 = ('mod_login1', 'mod_login2', 'new_mod_login')
# vips
ROOM_VIPS = TwitchIRCMsg(
    '@msg-id=vips_success NOTICE #target :The VIPs of this channel are: vip_login1, vip_login2, vip_login3.'
)
ROOM_VIPS2 = TwitchIRCMsg(
    '@msg-id=vips_success NOTICE #target :The VIPs of this channel are: vip_login1, vip_login2, new_vip_login.'
)
NO_VIPS = TwitchIRCMsg('@msg-id=no_vips :tmi.twitch.tv NOTICE #target :This channel does not have any VIPs.')
VIPS = ('vip_login1', 'vip_login2', 'vip_login3')
VIPS2 = ('vip_login1', 'vip_login2', 'new_vip_login')
# commands
ROOM_CMDS = TwitchIRCMsg(
    '@msg-id=cmds_available NOTICE #target :Commands available to you in this room (use /help <command> for details): '
    '/cmd1 /cmd2 /cmd3 More help: https://help.twitch.tv/s/article/chat-commands'
)
ROOM_CMDS2 = TwitchIRCMsg(
    '@msg-id=cmds_available NOTICE #target :Commands available to you in this room (use /help <command> for details): '
    '/cmd1 /cmd2 /new_cmd More help: https://help.twitch.tv/s/article/chat-commands'
)
NO_CMDS = TwitchIRCMsg('@msg-id=no_help NOTICE #target :No comands aviliable to you in this room')
CMDS = ('/cmd1', '/cmd2', '/cmd3')
CMDS2 = ('/cmd1', '/cmd2', '/new_cmd')
# all channel_parts
CHANNEL_PARTS = (GLOBALSTATE, ROOMSTATE, USERSTATE, NAMES_PART, NAMES_PART2, NAMES_END, ROOM_MODS, ROOM_VIPS, ROOM_CMDS)
PRIVMSG = TwitchIRCMsg('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                 'PRIVMSG #target :content with a @mention :(')
WHISPER = TwitchIRCMsg('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                'WHISPER target :content with a @mention :(')
JOIN = TwitchIRCMsg(':username!username@username.tmi.twitch.tv JOIN #target')
PART = TwitchIRCMsg(':username!username@username.tmi.twitch.tv PART #target')
NT_WHISPER_INVALID_SELF = TwitchIRCMsg('@msg-id=whisper_invalid_self NOTICE #target :You cannot whisper to yourself.')
NT_CHNL_SUSPENDED = TwitchIRCMsg('@msg-id=msg_channel_suspended NOTICE #target :This channel has been suspended.')
NT_FLWONLY_0 = TwitchIRCMsg('@msg-id=msg_followersonly_zero NOTICE #target :'
                    'This room is in followers-only mode. Follow target to join the community!')

CLEARCHAT_TIMEOUT = TwitchIRCMsg('@ban-duration=600;target-user-id=012345;target-msg-id=1-2-3 CLEARCHAT #target :username')
CLEARCHAT_BAN = TwitchIRCMsg('@target-user-id=012345;target-msg-id=1-2-3 CLEARCHAT #target :username')
CLEARCHAT = TwitchIRCMsg('@tmi-sent-ts=1629011347771 CLEARCHAT #target')
CLEARMSG = TwitchIRCMsg("@target-msg-id=1-2-3;login=username CLEARMSG #target :deleted message's content")
