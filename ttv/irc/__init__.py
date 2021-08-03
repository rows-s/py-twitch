from .client import Client
from .channel import Channel
from .messages import BaseMessage, ChannelMessage, ParentMessage, Whisper
from .users import BaseUser, ChannelUser, GlobalUser, ParentMessageUser
from .user_states import BaseState, GlobalState, LocalState
from .irc_message import IRCMessage
from . import events
from . import user_events
from . import exceptions


ANON_LOGIN = 'justinfan0'
ANON_TOKEN = ''
