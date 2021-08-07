import asyncio
from abc import ABC
from copy import copy
from functools import cached_property

from .utils import parse_raw_badges
from .irc_message import IRCMessage

from typing import Dict, Tuple, TypeVar

__all__ = ('BaseState', 'GlobalState', 'LocalState')


class BaseState(ABC):
    """Base class for user states and users"""

    def __init__(self, irc_msg: IRCMessage):
        self._raw_badges = irc_msg.tags.get('badges', '')
        self.id: str = irc_msg.tags.get('user-id')
        self.login: str = irc_msg.tags.get('user-login')
        self.display_name: str = irc_msg.tags.get('display-name')
        self.color: str = irc_msg.tags.get('color')

    @cached_property
    def badges(self) -> Dict[str, str]:
        return parse_raw_badges(self._raw_badges)

    def update(self, irc_msg: IRCMessage):
        self.__init__(irc_msg)
        del self.badges  # would be recalculated in the next call

    def copy(self):
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


class GlobalState(BaseState):
    """Class represents global state of a twitch-user :class:`ttv.irc.Client`"""
    def __init__(self, irc_msg: IRCMessage):
        super().__init__(irc_msg)
        self.emote_sets: Tuple[str] = tuple(irc_msg.tags.get('emote-sets', '').split(','))
        self.badge_info: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badge-info', ''))  # empty most times

    def copy(self):
        new = super().copy()
        new.badge_info = copy(self.badge_info)
        return new

    def __eq__(self, other):
        if isinstance(other, GlobalState):
            if super().__eq__(other):
                try:
                    assert self.emote_sets == other.emote_sets
                    assert self.badge_info == other.badge_info
                except AssertionError:
                    return False
                else:
                    return True
        return False


class LocalState(BaseState):
    """Class represents local state of a user in a :class:`ttv.irc.Channel`"""
    def __init__(self, irc_msg: IRCMessage):
        super().__init__(irc_msg)
        self._raw_badge_info = irc_msg.tags.get('badge-info', '')
        self.emote_sets: Tuple[str] = tuple(irc_msg.tags.get('emote-sets', '').split(','))

    @cached_property
    def badge_info(self) -> Dict[str, str]:
        return parse_raw_badges(self._raw_badge_info)

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

    def copy(self):
        new = super().copy()
        new.badge_info = copy(self.badge_info)
        return new

    def update(self, irc_msg: IRCMessage):
        super().update(irc_msg)
        del self.badge_info  # would be recalculated in the next call

    def __eq__(self, other):
        if isinstance(other, LocalState):
            if super().__eq__(other):
                try:
                    assert self.emote_sets == other.emote_sets
                    assert self.badge_info == other.badge_info
                except AssertionError:
                    return False
                else:
                    return True
        return False
