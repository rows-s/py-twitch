from .utils import escape_tag_value, unescape_tag_value

from typing import Tuple, Optional, Any, Dict, List, Iterable

__all__ = ('IRCMessage',)


class IRCMessage:
    def __init__(
            self,
            raw_irc_message: str
    ) -> None:
        # message
        self.raw_irc_message: str = raw_irc_message
        # parts
        self.raw_tags: Optional[str]
        self.prefix: Optional[str]
        self.command: str
        self.raw_params: Optional[str]
        self.raw_tags, self.prefix, self.command, self.raw_params = self._parse_raw_irc_message()
        # tags
        self.tags: Dict[str, Optional[str]]
        self.tags = self._parse_raw_tags()
        # prefix
        self.servername: Optional[str]
        self.nickname: Optional[str]
        self.user: Optional[str]
        self.host: Optional[str]
        self.servername, self.nickname, self.user, self.host = self._parse_prefix()
        # params
        self.params: List[str]
        self.middles: List[str]
        self.trailing: Optional[str]
        self.params, self.middles, self.trailing = self._parse_raw_params()
        self.content: Optional[str] = self.trailing

    def update_tags(
            self,
            tags: Dict[str, Any]
    ) -> None:
        if not tags:
            return
        self.tags.update(tags)
        self.set_tags(self.tags)

    def set_tags(
            self,
            tags: Dict[str, Optional[str]]
    ) -> None:
        # tags
        self.tags = tags
        # raw_tags
        self.raw_tags = self._join_tags(self.tags)
        # raw_irc_message
        if self.raw_irc_message.startswith('@'):
            no_tag_raw_irc_message = self.raw_irc_message.split(' ', 1)[1]
        else:
            no_tag_raw_irc_message = self.raw_irc_message
        if self.raw_tags is not None:
            self.raw_irc_message = f'@{self.raw_tags} {no_tag_raw_irc_message}'
        else:
            self.raw_irc_message = no_tag_raw_irc_message

    def pop_tag(
            self,
            key: str
    ) -> Optional[str]:
        value = self.tags.pop(key)
        self.set_tags(self.tags)
        return value

    def remove_tags(
            self,
            keys: Iterable[str]
    ) -> None:
        for key in keys:
            self.tags.pop(key, None)
        self.set_tags(self.tags)

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

    def _parse_raw_tags(self) -> Dict[str, Optional[str]]:
        tags = {}  # is not None if raw_params is None to exclude exceptions from: for, in, [key] etc.
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

    def _parse_prefix(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        prefix = self.prefix
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

    def _parse_raw_params(self) -> Tuple[Tuple, Tuple, Optional[str]]:
        # possible cases:             # middle may contain ':', trailing may contain ' ', ':', ' :'.
        # None                        # no params
        # 'middle'                    # middles, no trailing
        # 'middle :trailing'          # middles, trailing (starts with ':')
        # 'middle :trai :ling'        # same and trailing contains separators (' ', ':', ' :')
        # 'middle '*14 + 'trailing'   # middles(max), trailing (starts without ':')
        # 'middle '*14 + 'trai :ling' # same and trailing contains separators (' ', ':', ' :')
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
                    trailing = trailing.removeprefix(':')
                    middles = raw_parsed_params[:index]
                    params = middles + [trailing]
                    break
            else:
                # if trailing exists and starts without ':' (only if there is 14 of middles)
                if len(raw_parsed_params) == 15:
                    trailing = raw_parsed_params[14]  # not startswith ':'
                    middles = raw_parsed_params[:14]
                    params = raw_parsed_params
                # if trailing not exists
                else:
                    trailing = None
                    params = middles = raw_parsed_params

        return tuple(params), tuple(middles), trailing

    @staticmethod
    def _join_tags(tags: Dict[str, Any]):
        raw_tags_list = []
        if not tags:
            return None
        else:
            for key, value in tags.items():
                if value is not None:
                    value = escape_tag_value(value)
                    raw_tag = f'{key}={value}'
                else:
                    raw_tag = key
                raw_tags_list.append(raw_tag)
            return ';'.join(raw_tags_list)

    def __eq__(self, other) -> bool:
        if isinstance(other, IRCMessage):
            try:
                assert self.command == other.command
                assert self.prefix == other.prefix
                assert set(self.middles) == set(other.middles)  # sets to neglect params' positions. faster than sorted
                assert self.tags == other.tags
            except AssertionError:
                return False
            else:
                return True
        else:
            return False

    def __contains__(self, item) -> bool:
        if type(item) is str:
            return item in self.raw_irc_message
        elif isinstance(item, IRCMessage):
            return item.raw_irc_message in self.raw_irc_message
        return False

    def __repr__(self):
        return self.raw_irc_message

    def __str__(self):
        return self.__repr__()
