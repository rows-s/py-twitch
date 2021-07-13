from .. import exceptions

__all__ = (
    'ChannelNotExists',
    'LoginFailed',
    'UnknownEvent',
    'FunctionIsNotCorutine',
    'InvalidMessageStruct'
)


class ChannelNotExists(exceptions.ChannelNotExists):
    """Is raised if channel not exists"""


class LoginFailed(exceptions.LoginFailed):
    """Is raised if token or login is incorrect"""


class UnknownEvent(exceptions.UnknownEvent):
    """Is raised if trying to register an event with unknown name"""


class FunctionIsNotCorutine(exceptions.FunctionIsNotCorutine):
    """Is raised if trying to register an event handler that is not a coroutine"""


class InvalidMessageStruct(exceptions.InvalidMessageStruct):
    """Is raised if raw irc message has unexpected structure"""
