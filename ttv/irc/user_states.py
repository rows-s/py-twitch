from .utils import parse_raw_badges
from .irc_message import IRCMessage

from typing import Dict, Tuple

__all__ = ('GlobalState', 'LocalState')


class GlobalState:
    """This class represent global state of twitch-user (`irc.Client`)"""

    def __init__(self, irc_msg: IRCMessage):
        self.id: str = irc_msg.tags.get('user-id')
        self.login: str = irc_msg.tags.get('user-login')
        self.display_name: str = irc_msg.tags.get('display-name')
        self.emote_sets: Tuple[str] = tuple(irc_msg.tags.get('emote-sets', '').split(','))
        self.color: str = irc_msg.tags.get('color')
        # badges
        self.badges: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badges', ''))
        self.badge_info: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badge-info', ''))

    def __eq__(self, other):
        if isinstance(other, GlobalState):
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


class LocalState:
    """This class represent global state of ttv-user (`irc.Client`)"""

    def __init__(self, irc_msg: IRCMessage) -> None:
        self.id: str = irc_msg.tags.get('user-id')
        self.login: str = irc_msg.tags.get('user-login')
        self.display_name: str = irc_msg.tags.get('display-name')
        self.emote_sets = tuple(irc_msg.tags.get('emote-sets', '').split(','))
        # badges
        self.badges: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badges', ''))
        self.badge_info: Dict[str, str] = parse_raw_badges(irc_msg.tags.get('badge-info', ''))
        # local roles
        self.is_broadcaster: bool = 'broadcaster' in self.badges
        self.is_moderator: bool = 'moderator' in self.badges
        self.is_sub_gifter: bool = 'sub-gifter' in self.badges
        self.is_subscriber: bool = 'subscriber' in self.badges
        self.is_cheerer: bool = 'bits' in self.badges
        self.is_vip: bool = 'vip' in self.badges
        # roles values
        self.sub_gifter_count: int = int(self.badges.get('sub-gifter', 0))
        self.subscriber_mounths: int = int(self.badge_info.get('subscriber', 0))
        self.bits: int = int(self.badges.get('bits', 0))
