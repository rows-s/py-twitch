from .. import exceptions


__all__ = (
    'IRCException',
    'ChannelNotPrepared',
    'LoginFailed',
    'CapabilitiesReqError'
)


class IRCException(exceptions.TTVException):
    """Base exception for all package's exceptions"""


class ChannelNotPrepared(IRCException, exceptions.ChannelNotPrepared):
    """Is raised if channel not exists"""


class LoginFailed(IRCException, exceptions.LoginFailed):
    """Is raised if token or login is incorrect"""


class CapabilitiesReqError(IRCException, exceptions.CapabilitiesReqError):
    """Is raised if failed on capabilities request"""
