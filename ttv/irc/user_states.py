from .utils import parse_raw_badges
from .irc_message import IRCMessage

from typing import Dict, Tuple

__all__ = ('BaseState', 'GlobalState', 'LocalState')


class BaseState:
    """Base class for user states"""

    def __init__(self, irc_msg: IRCMessage):
        self.id: str = irc_msg.tags.get('user-id')
        self.login: str = irc_msg.tags.get('user-login')
        self.display_name: str = irc_msg.tags.get('display-name')
        self.emote_sets: Tuple[str] = tuple(irc_msg.tags.get('emote-sets', '').split(','))
        self.color: str = irc_msg.tags.get('color')
        # badges
        self.badges: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badges', ''))
        self.badge_info: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badge-info', ''))

    def update(self, irc_msg: IRCMessage):
        self.__init__(irc_msg)

    def __eq__(self, other):
        if isinstance(other, BaseState):
            try:
                assert self.id == other.id
                assert self.login == other.login
                assert self.display_name == other.display_name
                assert self.emote_sets == other.emote_sets
                assert self.color == other.color
                assert self.badges == other.badges
                assert self.badge_info == other.badge_info
            except AssertionError:
                return False
            else:
                return True
        return False


class GlobalState(BaseState):
    """Class represents global state of a twitch-user :class:`ttv.irc.Client`"""


class LocalState(BaseState):
    """Class represents local state of a user (:class:`ttv.irc.Client`) in a channel (:class:`ttv.irc.Channel`)"""

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
