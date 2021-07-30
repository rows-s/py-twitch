__all__ = (
    'TTVException',
    'LoginFailed',
    'HTTPError',
    'InvalidToken',
    'ChannelNotPrepared',
    'CapabilitiesReqError'
)


class TTVException(Exception):
    """Base exception for all package's exceptions"""


class LoginFailed(TTVException):
    """Is raised if token or login is incorrect"""


class HTTPError(TTVException):
    pass


class InvalidToken(TTVException):
    pass


class ChannelNotPrepared(TTVException):
    pass


class CapabilitiesReqError(TTVException):
    pass
