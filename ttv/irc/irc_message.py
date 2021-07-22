from .utils import escape_tag_value, unescape_tag_value

from typing import Tuple, Optional, Any, Dict, List, Iterable

__all__ = ('IRCMessage',)


class IRCMessage:
    def __init__(
            self,
            raw_irc_msg: str
    ) -> None:
        self.command: str
        raw_tags, prefix, self.command, raw_params = self._parse_raw_irc_msg(raw_irc_msg)
        # tags
        self.tags: Dict[str, Optional[str]] = self._parse_raw_tags(raw_tags)
        # prefix
        self.servername: Optional[str]
        self.nickname: Optional[str]
        self.user: Optional[str]
        self.host: Optional[str]
        self.servername, self.nickname, self.user, self.host = self._parse_prefix(prefix)
        # params
        self.params: Tuple[str]
        self.middles: Tuple[str]
        self.trailing: Optional[str]
        self.channel: Optional[str]
        self.params, self.middles, self.trailing, self.channel = self._parse_raw_params(raw_params)
        self.content: Optional[str] = self.trailing

    @classmethod
    def create_empty(cls):
        return cls('COMMAND')

    @staticmethod
    def _parse_raw_irc_msg(
            raw_irc_msg
    ) -> Tuple[Optional[str], Optional[str], str, Optional[str]]:
        raw_irc_message = raw_irc_msg
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

    @staticmethod
    def _parse_raw_tags(
            raw_tags: Optional[str]
    ) -> Dict[str, Optional[str]]:
        tags = {}  # is not None if raw_params is None to exclude exceptions from: for, in, [key] etc.
        if raw_tags:  # parses only if there is raw_tags
            parsed_tags = raw_tags.split(';')
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

    @staticmethod
    def _parse_prefix(
            prefix: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        servername = None  # better than do it within conditions
        nickname = None
        user = None
        host = None
        if prefix:  # may be None
            if '@' in prefix:
                prefix, host = prefix.split('@', 1)
                if '!' in prefix:
                    nickname, user = prefix.split('!', 1)
                else:
                    nickname = prefix
            else:
                if '.' in prefix:  # local agreement that there are not dots in nicknames
                    servername = prefix
                else:
                    nickname = prefix
        return servername, nickname, user, host

    @staticmethod
    def _parse_raw_params(
            raw_params: Optional[str]
    ) -> Tuple[Tuple, Tuple, Optional[str], Optional[str]]:
        # possible cases:             # middle may contain ':', trailing may contain ' ', ':', ' :'.
        # None                        # no params
        # 'middle'                    # middles, no trailing
        # 'middle :trailing'          # middles, trailing (starts with ':')
        # 'middle :trai :ling'        # same and trailing contains separators (' ', ':', ' :')
        # 'middle '*14 + 'trailing'   # middles(max), trailing (starts without ':')
        # 'middle '*14 + 'trai :ling' # same and trailing contains separators (' ', ':', ' :')
        # ':trailing'                 # no middle, trailing

        params = []
        middles = []
        trailing = None
        channel = None
        if raw_params:
            raw_parsed_params = raw_params.split(' ', 14)
            for index, param in enumerate(raw_parsed_params):
                # if channel
                if param.startswith('#'):
                    channel = param[1:]
                # if trailing exists and starts with ':'
                elif param.startswith(':'):
                    trailing = ' '.join(raw_parsed_params[index:])
                    trailing = trailing.removeprefix(':')
                    middles = raw_parsed_params[:index]
                    params = middles + [trailing]
                    break  # avoidance else-block
            else:
                # if trailing exists and starts without ':' (only if there is 14 of middles)
                if len(raw_parsed_params) == 15:
                    trailing = raw_parsed_params[14]  # not startswith ':'
                    middles = raw_parsed_params[:14]
                    params = raw_parsed_params
                # if trailing not exists
                else:
                    params = middles = raw_parsed_params

        return tuple(params), tuple(middles), trailing, channel

    def _join_tags(self) -> Optional[str]:
        if not self.tags:
            return None
        else:
            raw_tags_list = []
            for key, value in self.tags.items():
                if value is not None:
                    raw_tag = f'{key}={escape_tag_value(value)}'
                else:
                    raw_tag = key
                raw_tags_list.append(raw_tag)
            return ';'.join(raw_tags_list)

    def _join_prefix_parts(self) -> Optional[str]:
        if self.servername is not None:
            prefix = self.servername
        if self.nickname is not None:
            prefix = self.nickname
            if self.host is not None:
                if self.user is not None:
                    prefix += f'!{self.user}@{self.host}'
                else:
                    prefix += f'@{self.host}'
        else:
            prefix = None
        return prefix

    def _join_params(self) -> Optional[str]:
        if not self.params:
            return None
        else:
            raw_params = ' '.join(self.middles)
            raw_params += f' :{self.trailing}' if self.trailing is not None else ''
            return raw_params

    def __eq__(self, other) -> bool:
        if isinstance(other, IRCMessage):
            try:
                assert self.command == other.command
                assert self.servername == other.servername
                assert self.nickname == other.nickname
                assert self.host == other.host
                assert self.user == other.user
                assert set(self.middles) == set(other.middles)
                assert self.tags == other.tags
            except AssertionError:
                return False
            else:
                return True

    def __repr__(self):
        raw_tags = self._join_tags()
        raw_irc_message = f'@{raw_tags} ' if raw_tags is not None else ''
        prefix = self._join_prefix_parts()
        raw_irc_message += f':{prefix} ' if prefix is not None else ''
        raw_irc_message += self.command
        raw_params = self._join_params()
        raw_irc_message += f' {raw_params}' if raw_params is not None else ''
        return raw_irc_message

    def __str__(self):
        return self.__repr__()
