from .. import exceptions


class InvalidToken(exceptions.InvalidToken):
    """Is raised if can't call """


class HTTPError(exceptions.HTTPError):
    """IS raised if http response contains status different from 2XX"""

