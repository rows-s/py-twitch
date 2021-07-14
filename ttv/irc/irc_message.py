from .utils import unescape_tag_value
from typing import Dict, Tuple, Optional

__all__ = ('IRCMessage',)


class IRCMessage:
    # noinspection PyTypeChecker
    def __init__(
            self,
            raw_irc_message: str
    ) -> None:
        # message
        self.raw_irc_message: str = raw_irc_message

        self.raw_tags, self.prefix, self.command, self.raw_params = self._parse_raw_irc_message()
        self.tags = self._parse_raw_tags()
        self.servername, self.nickname, self.user, self.host = self._parse_prefix()
        self.params, self.middles, self.trailing = self._parse_raw_params()
        self.content = self.trailing

    def _parse_raw_irc_message(self) -> Tuple[Optional[str], Optional[str], str, Optional[str]]:
        raw_irc_message = self.raw_irc_message
        # tags
        if raw_irc_message.startswith('@'):  # at least one tag, ends with ' '
            raw_tags, raw_irc_message = raw_irc_message[1:].split(' ', 1)
        else:
            raw_tags = None
        # prefix
        if raw_irc_message.startswith(':'):  # if starts with ':' then contains prefix. ends with ' '
            prefix, raw_irc_message = raw_irc_message[1:].split(' ', 1)
        else:
            prefix = None
        # command & raw_params
        try:
            command, raw_params = raw_irc_message.split(' ', 1)
        # if has not params
        except ValueError:
            command = raw_irc_message
            raw_params = None
        return raw_tags, prefix, command, raw_params

    def _parse_raw_tags(self):
        tags = {}  # not is None if raw_params is None to exclude any checking before: for, in, __index__ and other
        if self.raw_tags:  # parses only if there is raw_tags
            parsed_tags = self.raw_tags.split(';')
            for raw_tag in parsed_tags:
                # if has value
                try:
                    key, value = raw_tag.split('=', 1)
                    value = unescape_tag_value(value)
                # if has not value
                except ValueError:
                    key = raw_tag
                    value = None
                tags[key] = value
        return tags

    def _parse_prefix(self):
        prefix = self.prefix
        servername = None
        nickname = None
        user = None
        host = None
        if prefix:  # may ne None
            if '@' in prefix:
                prefix, host = prefix.split('@', 1)
                if '!' in prefix:
                    nickname, user = prefix.split('!', 1)
                else:
                    nickname = prefix
            else:
                if '.' in prefix:
                    servername = prefix
                else:
                    nickname = prefix
        return servername, nickname, user, host

    def _parse_raw_params(self) -> Tuple[Tuple, Tuple, Optional[str]]:
        # possible cases:             # middle may contain ':', trailing may contain ' ', ':', ' :'.
        # None                        # no params
        # 'middle'                    # middles, no trailing
        # 'middle :trailing'          # middles, trailing (starts with ':')
        # 'middle '*14 + 'trailing'   # middles(max), trailing (starts without ':')
        # ':trailing'                 # no middle, trailing

        # if has not params
        if not self.raw_params:
            params = ()
            middles = ()
            trailing = None
        # if has params
        else:
            raw_parsed_params = self.raw_params.split(' ', 14)
            for index, param in enumerate(raw_parsed_params):
                # if trailing exists and starts with ':'
                if param.startswith(':'):
                    trailing = ' '.join(raw_parsed_params[index:])
                    trailing = trailing[1:]
                    middles = raw_parsed_params[:index]
                    params = middles + [trailing]
                    break
            else:
                # if trailing exists and starts without ':' (only if there is 14 of middles)
                if len(raw_parsed_params) == 15:
                    trailing = raw_parsed_params[14]
                    middles = raw_parsed_params[:14]
                    params = raw_parsed_params
                # if trailing not exists
                else:
                    trailing = None
                    middles = raw_parsed_params
                    params = raw_parsed_params
        return tuple(params), tuple(middles), trailing

    def __eq__(self, other) -> bool:
        if type(other) is IRCMessage:
            return self.raw_irc_message == other.raw_irc_message
        return False

    def __contains__(self, item) -> bool:
        if type(item) is str:
            return item in self.raw_irc_message
        return False

    def __repr__(self):
        return self.raw_irc_message

    def __str__(self):
        return self.__repr__()
