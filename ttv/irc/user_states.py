import asyncio
from abc import ABC
from copy import copy

from .utils import parse_raw_badges
from .irc_message import IRCMessage

from typing import Dict, Tuple, TypeVar

__all__ = ('BaseState', 'BaseExtState', 'GlobalState', 'LocalState')

_T = TypeVar('_T')


class BaseState(ABC):
    """Base class for user states and users"""

    def __init__(self, irc_msg: IRCMessage):
        self.id: str = irc_msg.tags.get('user-id')
        self.login: str = irc_msg.tags.get('user-login')
        self.display_name: str = irc_msg.tags.get('display-name')
        self.color: str = irc_msg.tags.get('color')
        self.badges: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badges', ''))

    def update(self, irc_msg: IRCMessage):
        self.__init__(irc_msg)

    def copy(self: _T) -> _T:
        new = copy(self)
        new.badges = copy(self.badges)
        return new

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseState):
            try:
                assert self.id == other.id
                assert self.login == other.login
                assert self.display_name == other.display_name
                assert self.color == other.color
                assert self.badges == other.badges
            except AssertionError:
                return False
            else:
                return True
        return False


class BaseExtState(BaseState, ABC):
    """Base state with extensioned ::"""
    def __init__(self, irc_msg: IRCMessage):
        super(BaseExtState, self).__init__(irc_msg)
        self.emote_sets: Tuple[str] = tuple(irc_msg.tags.get('emote-sets', '').split(','))
        self.badge_info: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badge-info', ''))

    def copy(self: _T) -> _T:
        new = super(BaseExtState, self).copy()
        new.badge_info = copy(self.badge_info)
        return new

    def __eq__(self, other):
        if isinstance(other, BaseExtState):
            if super(BaseExtState, self).__eq__(other):
                try:
                    assert self.emote_sets == other.emote_sets
                    assert self.badge_info == other.badge_info
                except AssertionError:
                    return False
                else:
                    return True
        return False


class GlobalState(BaseExtState):
    """Class represents global state of a twitch-user :class:`ttv.irc.Client`"""


class LocalState(BaseExtState, ABC):
    """Class represents local state of a user in a :class:`ttv.irc.Channel`"""

    @property
    def is_broadcaster(self) -> bool:
        return 'broadcaster' in self.badges

    @property
    def is_moderator(self) -> bool:
        return 'moderator' in self.badges

    @property
    def is_sub_gifter(self) -> bool:
        return 'sub-gifter' in self.badges

    @property
    def is_subscriber(self) -> bool:
        return 'subscriber' in self.badges

    @property
    def is_cheerer(self) -> bool:
        return 'bits' in self.badges

    @property
    def is_vip(self) -> bool:
        return 'vip' in self.badges

    @property
    def sub_gifter_lvl(self) -> int:
        return int(self.badges.get('sub-gifter', 0))

    @property
    def subscriber_mounths(self) -> int:
        return int(self.badge_info.get('subscriber', 0))

    @property
    def bits(self) -> int:
        return int(self.badges.get('bits', 0))
