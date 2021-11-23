from copy import copy
from typing import Tuple, Optional, Dict, Union

from .utils import escape_tag_value, unescape_tag_value

__all__ = ('IRCMsg', 'TwitchIRCMsg')


class IRCMsg:
    def __init__(
            self,
            raw_irc_msg: str
    ) -> None:
        self.command: str
        # raw_tags
        self.tags: Dict[str, Optional[str]]
        # prefix
        self.servername: Optional[str]
        self.nickname: Optional[str]
        self.user: Optional[str]
        self.host: Optional[str]
        # raw_params
        self.middles: Tuple[str]
        self.trailing: Optional[str]
        # whole logic within it
        self._parse_raw_irc_msg(raw_irc_msg)

    @classmethod
    def create_empty(cls):
        return cls('EMPTY')

    def get(self, key, default=None) -> Optional[str]:
        return self.tags.get(key, default)

    def items(self):
        for item in self.tags.items():
            yield item

    def update(self, item: Union['IRCMsg', Dict]):
        if isinstance(item, IRCMsg):
            self.tags.update(item.tags)
        elif isinstance(item, dict):
            self.tags.update(item)

    def copy(self):
        new = copy(self)
        new.tags = self.tags.copy()
        return new

    def _parse_raw_irc_msg(
            self,
            raw_irc_msg: str
    ):
        raw_tags = None
        prefix = None
        raw_params = None

        if raw_irc_msg.startswith('@'):
            raw_tags, raw_irc_msg = raw_irc_msg[1:].split(' ', 1)  # at least one tag. Ends with ' '
        if raw_irc_msg.startswith(':'):
            prefix, raw_irc_msg = raw_irc_msg[1:].split(' ', 1)  # ends with ' '
        try:
            command, raw_params = raw_irc_msg.split(' ', 1)
        except ValueError:
            command = raw_irc_msg  # if has not params

        self.command: str = command

        self._parse_raw_tags(raw_tags)  # tags
        self._parse_prefix(prefix)  # servername, nickname, user, host
        self._parse_raw_params(raw_params)  # middles, trailing

        return raw_tags, prefix, raw_params

    def _parse_raw_tags(
            self,
            raw_tags: Optional[str]
    ):
        tags = {}  # is not None if raw_params is None to exclude exceptions from: for, in, .get() etc.

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

        self.tags: Dict[str, Optional[str]] = tags

    def _parse_prefix(
            self,
            prefix: Optional[str]
    ):
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

        self.servername: Optional[str] = servername
        self.nickname: Optional[str] = nickname
        self.user: Optional[str] = user
        self.host: Optional[str] = host

    def _parse_raw_params(
            self,
            raw_params: Optional[str]
    ):

        middles = ()
        trailing = None

        if raw_params:
            raw_parsed_params = raw_params.split(' ', 14)
            for index, param in enumerate(raw_parsed_params):
                # if trailing exists and starts with ':'
                if param.startswith(':'):
                    middles = raw_parsed_params[:index]
                    trailing = ' '.join(raw_parsed_params[index:])
                    trailing = trailing.removeprefix(':')
                    break  # avoidance else-block
            else:
                # if trailing exists and starts without ':' (only if there is 14 of middles)
                if len(raw_parsed_params) == 15:
                    middles = raw_parsed_params[:14]
                    trailing = raw_parsed_params[14]  # not startswith ':'
                # if trailing not exists
                else:
                    middles = raw_parsed_params

        self.middles: Tuple[str] = tuple(middles)
        self.trailing: Optional[str] = trailing

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
        elif self.nickname is not None:
            prefix = self.nickname
            if self.host is not None:
                if self.user is not None:
                    prefix += f'!{self.user}'
                prefix += f'@{self.host}'
        else:
            prefix = None
        return prefix

    def _join_params(self) -> Optional[str]:
        if not self.middles and not self.trailing:
            return None
        else:
            raw_params = ' '.join(self.middles)
            raw_params += f' :{self.trailing}' if self.trailing is not None else ''
            return raw_params

    def __eq__(self, other) -> bool:
        if isinstance(other, TwitchIRCMsg):
            try:
                assert self.command == other.command
                assert self.servername == other.servername
                assert self.nickname == other.nickname
                assert self.host == other.host
                assert self.user == other.user
                assert self.tags == other.tags
                assert set(self.middles) == set(other.middles)
                assert self.trailing == other.trailing
            except AssertionError:
                return False
            else:
                return True

    def __getitem__(self, item) -> Optional[str]:
        return self.tags[item]

    def __setitem__(self, key, value):
        self.tags[key] = value

    def __contains__(self, item) -> bool:
        return item in self.tags

    def __iter__(self):
        for key in self.tags:
            yield key

    def __repr__(self):
        raw_tags = f'@{raw_tags} ' if (raw_tags := self._join_tags()) is not None else ''
        prefix = f':{prefix} ' if (prefix := self._join_prefix_parts()) is not None else ''
        raw_params = f' {raw_params}' if (raw_params := self._join_params()) is not None else ''
        return f'{raw_tags}{prefix}{self.command}{raw_params}'

    def __str__(self):
        return self.__repr__()


class TwitchIRCMsg(IRCMsg):
    def __init__(self, raw_irc_msg: str):
        super().__init__(raw_irc_msg)
        self.channel: Optional[str] = self._get_channel()
        self.msg_id: Optional[str] = self.tags.get('msg-id')

    def _get_channel(self) -> Optional[str]:
        for middle in self.middles:
            if middle.startswith('#'):
                return middle[1:]
        else:
            return None
