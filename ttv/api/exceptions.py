from .. import exceptions


class APIException(exceptions.TTVException):
    """Base exception for all package's exceptions"""


class InvalidToken(APIException, exceptions.InvalidToken):
    """Is raised if can't call """


class HTTPError(APIException, exceptions.HTTPError):
    """IS raised if http response contains status different from 2XX"""

