class TTVException(Exception):
    """Base exception for all package's exceptions"""


class FunctionIsNotCorutine(TTVException):
    """Is raised if expected an async function but got not an async function"""


class LoginFailed(TTVException):
    """Is raised if token or login is incorrect"""


class UnknownEvent(TTVException):
    """Is raised if got not known event name"""


class UnknownRoomState(TTVException):
    pass


class UnknownHostTarget(TTVException):
    pass


class UnknownCommand(TTVException):
    pass


class HTTPError(TTVException):
    pass


class InvalidToken(TTVException):
    pass


class WrongIterObjects(TTVException):
    pass


class ServerError(TTVException):
    pass


class AccessError(TTVException):
    pass


class ChannelNotExists(TTVException):
    pass


class InvalidChannelName(TTVException):
    pass


class CapabilitiesReqError(TTVException):
    pass
