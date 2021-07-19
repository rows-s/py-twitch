__all__ = (
    'TTVException',
    'FunctionIsNotCoroutine',
    'LoginFailed',
    'UnknownEvent',
    'HTTPError',
    'InvalidToken',
    'ChannelNotPrepared',
    'CapabilitiesReqError'
)


class TTVException(Exception):
    """Base exception for all package's exceptions"""


class FunctionIsNotCoroutine(TTVException):
    """Is raised if expected an async function but got not an async function"""


class LoginFailed(TTVException):
    """Is raised if token or login is incorrect"""


class UnknownEvent(TTVException):
    """Is raised if got not known event name"""


class HTTPError(TTVException):
    pass


class InvalidToken(TTVException):
    pass


class ChannelNotPrepared(TTVException):
    pass


class CapabilitiesReqError(TTVException):
    pass
