__all__ = (
    'TTVException',
    'FunctionIsNotCorutine',
    'LoginFailed',
    'UnknownEvent',
    'HTTPError',
    'InvalidToken',
    'ChannelNotExists',
    'CapabilitiesReqError'
)


class TTVException(Exception):
    """Base exception for all package's exceptions"""


class FunctionIsNotCorutine(TTVException):
    """Is raised if expected an async function but got not an async function"""


class LoginFailed(TTVException):
    """Is raised if token or login is incorrect"""


class UnknownEvent(TTVException):
    """Is raised if got not known event name"""


class HTTPError(TTVException):
    pass


class InvalidToken(TTVException):
    pass


class ChannelNotExists(TTVException):
    pass


class CapabilitiesReqError(TTVException):
    pass
