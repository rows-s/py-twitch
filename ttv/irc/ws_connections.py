

class IRCConnection:
    def __init__(
            self,
            uri: str,
            *,
            keep_alive: bool
    ):
        self._uri = uri
        self._keep_alive: bool = keep_alive

    async def __aiter__(self):
        pass
