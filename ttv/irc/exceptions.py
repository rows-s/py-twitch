from .. import exceptions


__all__ = (
    'ChannelNotExists',
    'LoginFailed',
    'UnknownEvent',
    'FunctionIsNotCorutine',
    'CapabilitiesReqError'
)


class IRCException(exceptions.TTVException):
    """Base exception for all package's exceptions"""


class ChannelNotExists(IRCException, exceptions.ChannelNotExists):
    """Is raised if channel not exists"""


class LoginFailed(IRCException, exceptions.LoginFailed):
    """Is raised if token or login is incorrect"""


class UnknownEvent(IRCException, exceptions.UnknownEvent):
    """Is raised if trying to register an event with unknown name"""


class FunctionIsNotCorutine(IRCException, exceptions.FunctionIsNotCoroutine):
    """Is raised if trying to register an event handler that is not a coroutine"""


class CapabilitiesReqError(IRCException, exceptions.CapabilitiesReqError):
    """Is raised if failed on capabilities request"""
