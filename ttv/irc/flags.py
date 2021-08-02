from typing import Tuple, Iterable


__all__ = ('FlagIDs', 'Flag')


class FlagIDs:
    def __init__(self, *ids: str):
        self.ids: Tuple[str] = ids

    @property
    def has_empty_id(self):
        return '' in self.ids

    def has_sub_id(self, id_type: str) -> bool:
        for _id in self.ids:
            if _id.startswith(id_type):
                return True
        else:
            return False

    def __iter__(self):
        return self.ids.__iter__()

    def __contains__(self, item):
        if isinstance(item, FlagIDs):
            for flag_id in item:
                if flag_id not in self.ids:
                    return False
            else:
                return True
        elif isinstance(item, str):
            return item in self.ids
        else:
            return False

    def __eq__(self, other):
        return self.__contains__(other)


class Flag(FlagIDs):
    """
    Class represents a flag with its ids and position(start, end).

    Attributes:


    Examples:
        >>> content = 'OMG, hello https://twitch.tv bitch'
        >>> flag = Flag(('P.0',) , 'OMG', 0, 3)
        >>> flag2 = Flag(('',), 'https://twitch.tv', 11, 17)
        >>> flag3 = Flag(('A.7', 'I.5', 'P.6'), 'bitch', 29, 16)
        >>> flags = (flag, flag3, flag2)
        >>> content[flag.start:flag.end] == flag.content
        True
        >>> # Checking if there is an id in a flag
        >>> 'P.6' in flag3
        True
        >>> # __eq__(==) is the same with __containts__(in) so you can check if there is an id in flags
        >>> 'P.0' in flags
        True
        >>> # Checking if there are ids in a flag (if there is a flag from `flags` that contains each id of given flag)
        >>> FlagIDs('I.5', 'P.6') in flags
        True
        >>> # Checking if there is a sub id (an id starts with 'I')
        >>> flag.has_sub_id('I')
        False
        >>> flag3.has_sub_id('I')
        True
        >>> # Checking if there is an empty id (need cause every `str` starts with '')
        >>> flag2.has_empty_id
        True
    """

    def __init__(self, ids: Iterable[str], content: str, start: int, end: int):
        super(Flag, self).__init__(*ids)
        self.content: str = content
        self.start: int = start
        self.end: int = end

    @property
    def position(self) -> Tuple[int, int]:
        return self.start, self.end

    def __str__(self):
        return f'flag {self.ids} in position {self.position} :{self.content}'
