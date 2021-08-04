from ttv.irc import IRCMessage


CAP = IRCMessage(':tmi.twitch.tv CAP * ACK :twitch.tv/membership twitch.tv/commands twitch.tv/tags')
GS = IRCMessage('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 GLOBALUSERSTATE')
RS = IRCMessage('@emote-only=0;followers-only=-1;r9k=0;rituals=0;room-id=12345;slow=0;subs-only=0 ROOMSTATE #target')
NP = IRCMessage('353 #target :username username2 username3')
NP2 = IRCMessage('353 #target :username4 username5 username6')
NE = IRCMessage('366 #target')
NAMES = tuple(['username', 'username2', 'username3'] + ['username4', 'username5', 'username6'])
US = IRCMessage('@badges=;badge-info=;color=;display-name=Target;emote-sets=;user-id=12345 USERSTATE #target')
CHANNEL_PARTS = (GS,RS, NP, NP2, NE, US)
MSG = IRCMessage('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                 'PRIVMSG #target :content with a @metion :(')
WP = IRCMessage('@display-name=UserName;emotes=555555558:23-24 :username!username@username.tmi.twitch.tv '
                'WHISPER target :content with a @metion :(')
JN = IRCMessage(':username!username@username.tmi.twitch.tv JOIN #target')
PT = IRCMessage(':username!username@username.tmi.twitch.tv PART #target')
