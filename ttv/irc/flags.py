from abc import ABC
from typing import Tuple, Iterable, Generator

__all__ = ('BaseFlag', 'Flag', 'SubFlag')


class BaseFlag(ABC):
    def __init__(self, content: str, start: int, end: int):
        self.content: str = content
        self.start: int = start
        self.end: int = end

    @property
    def position(self) -> Tuple[int, int]:
        return self.start, self.end


class SubFlag(BaseFlag):
    """Class represents a sub flag with its id, content, and position(start, end)."""
    def __init__(self, id_: str, content: str, start: int, end: int):
        super(SubFlag, self).__init__(content, start, end)
        self.id: str = id_

    def __str__(self):
        return f'Flag {self.id} in position {self.position} :{self.content}'


class Flag(BaseFlag):
    """
    Class represents a flag with its ids, content, and position(start, end).

    Examples:
        >>> content = 'OMG, hello https://twitch.tv bitch'
        >>> flag = Flag(('P.0',) , 'OMG', 0, 3)
        >>> flag2 = Flag(('',), 'https://twitch.tv', 11, 28)
        >>> flag3 = Flag(('A.6', 'I.5', 'P.6'), 'bitch', 29, 34)
        >>> flags = (flag, flag2, flag3)
        >>> assert content[flag.start:flag.end] == flag.content
        >>> # Checking if there is an id in a flag
        >>> assert 'P.6' in flag3
        >>> # Checking if there is a flag from `flags` that contains given id
        >>> assert 'P.0' in flags
        >>> # Checking if there are ids in a flag
        >>> assert ('I.5', 'P.6') in flag3
        >>> # Checking if there is a flag from `flags` that contains each given id
        >>> assert ('I.5', 'P.6') in flags
        >>> # Checking if there is a sub id (an id starts with 'I')
        >>> assert flag.has_sub_id('P')
        >>> assert flag3.has_sub_id('I')
        >>> # Checking if there is an empty id
        >>> assert '' in flag2
        >>> # For take each id as a single sub flag use __iter__(in) yeilds :class:`SubFlag`
        >>> for sub_flag in flag3:
        ...     print(sub_flag)
        Flag A.6 in position (29, 34) :bitch
        Flag I.5 in position (29, 34) :bitch
        Flag P.6 in position (29, 34) :bitch
    """

    def __init__(self, ids: Iterable[str], content: str, start: int, end: int):
        """
        Args:
            ids (Tuple[str]):
                tuple with each id of the flag
            content (str):
                flagged part of message content
            start (int):
                position of the first symbol of the flagged content in the message content
            end (int):
                position of the last symbol (+1) of the flagged content in the message content
        """
        super(Flag, self).__init__(content, start, end)
        self.ids: Tuple[str] = tuple(ids)

    @property
    def has_empty_id(self):
        return '' in self.ids

    def has_sub_id(self, id_type: str) -> bool:
        for _id in self.ids:
            if _id.startswith(id_type):
                return True
        else:
            return False

    def __iter__(self) -> Generator[SubFlag, None, None]:
        for _id in self.ids:
            yield SubFlag(_id, self.content, self.start, self.end)

    def __contains__(self, item):
        if isinstance(item, str):
            return item in self.ids
        elif hasattr(item, '__iter__'):
            if item:  # must be one of list, tuple, set, dict etc. those return False if are empty.
                for sub_item in item:
                    if sub_item not in self.ids:
                        return False
                else:
                    return True
        return False

    def __eq__(self, other):
        return self.__contains__(other)

    def __str__(self):
        return f'Flags {self.ids} in position {self.position} :{self.content}'
