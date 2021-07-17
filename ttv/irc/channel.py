from .utils import parse_raw_badges

from typing import Dict, Tuple, Optional, Callable

__all__ = ('Channel',)


class Channel:
    def __init__(
            self,
            tags: Dict[str, str],
            _websocket_send: Callable
    ) -> None:
        # stable
        self.login: str = tags.get('room-login')
        self.id: str = tags.get('room-id')
        # out of tags
        self.my_state: Optional[LocalState] = None
        self.nameslist: Optional[Tuple[str]] = None
        # chat configuration
        self.is_unique_only: bool = tags.get('r9k') == '1'
        self.is_emote_only: bool = tags.get('emote-only') == '1'
        self.is_subs_only: bool = tags.get('subs-only') == '1'
        self.has_rituals: bool = tags.get('rituals') == '1'
        # slow configuration
        self.slow_seconds: int = int(tags.get('slow', 0))
        self.is_slow: bool = self.slow_seconds != 0
        # follower-only conficuration
        self.followers_only_minutes = int(tags.get('followers-only', 0))
        self.is_followers_only: bool = self.followers_only_minutes != -1  # -1 -> is off, otherwise -> is on
        # callback
        self._websocket_send: Callable = _websocket_send

    def update_values(
            self,
            tags: Dict[str, str]
    ) -> None:
        # if unique-only
        for key in tags:
            value = tags[key]
            if key == 'r9k':
                self.is_unique_only: bool = value == '1'
            # if emote-only
            elif key == 'emote-only':
                self.is_emote_only: bool = value == '1'
            # if subs-only
            elif key == 'subs-only':
                self.is_subs_only: bool = value == '1'
            # if rituals
            elif key == 'rituals':
                self.has_rituals: bool = value == '1'
            # if slow
            elif key == 'slow':
                self.slow_seconds: int = int(value)
                self.is_slow: bool = self.slow_seconds != 0
            # if followers-only
            elif key == 'followers-only':
                self.followers_only_minutes: int = int(value)
                self.is_followers_only: bool = self.followers_only_minutes != -1

    async def send_message(
            self,
            conntent: str
    ) -> None:
        await self._websocket_send(f'PRIVMSG #{self.login} :{conntent}')

    async def update(self):
        await self._websocket_send(f'JOIN #{self.login}')

    async def clear(self):
        await self.send_message('/clear')


class LocalState:
    def __init__(self, tags: Dict[str, str]) -> None:
        # stable tags
        self.display_name: str = tags.get('display-name')
        self.emote_sets = tuple(tags.get('emote-sets', '').split(','))
        # badges
        self.badges: Dict[str, str] = parse_raw_badges(tags.get('badges', ''))
        self.badge_info: Dict[str, str] = parse_raw_badges(tags.get('badge-info', ''))
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
