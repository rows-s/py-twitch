from .users import ChannelMember
from .channel import Channel

from .utils import unescape_tag_value, parse_raw_emotes

from abc import ABC
from typing import Dict, List, Tuple

__all__ = (
    'BaseUserEvent',
    'BaseSub',
    'ReSub',
    'Sub',
    'BaseGift',
    'SubMysteryGift',
    'SubGift',
    'GiftPaidUpgrade',
    'PrimePaidUpgrade',
    'BasePayForward',
    'StandardPayForward',
    'CommunityPayForward',
    'Raid',
    'UnRaid',
    'BitsBadgeTier',
    'Ritual',
)


class BaseUserEvent(ABC):
    """Base class for all IRC user events"""
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        self.author: ChannelMember = author
        self.channel: Channel = channel
        self.content: str = content
        # tags
        self.id: str = tags.get('id')
        self.time: int = int(tags.get('tmi-sent-ts', 0))
        self.flags: str = tags.get('flags')
        # emotes
        self.emote_only: bool = tags.get('emote-only') == '1'
        self.emotes: Dict[str, List[Tuple[int, int]]] = parse_raw_emotes(tags.get('emotes', ''))
        self.system_message: str = unescape_tag_value(tags.get('system-msg', ''))
        self.event_type: str = tags.get('msg-id')


#################################
# SUBS
#
class BaseSub(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        # months
        self.months: int = int(tags.get('msg-param-months', 0))
        self.comulative_months: int = int(tags.get('msg-param-cumulative-months', 0))
        # multimonth
        self.multimonth_duration: int = int(tags.get('msg-param-multimonth-duration', 0))
        self.multimonth_tenure: int = int(tags.get('msg-param-multimonth-tenure', 0))
        # streak
        self.has_streak: bool = tags.get('msg-param-should-share-streak') == '1'
        self.streak_months: int = int(tags.get('msg-param-streak-months', 0))
        # plan
        self.plan: str = tags.get('msg-param-sub-plan')
        self.plan_name: str = unescape_tag_value(tags.get('msg-param-sub-plan-name', ''))
        # is gifted
        self.is_gifted: bool = tags.get('msg-param-was-gifted') == 'true'


class ReSub(BaseSub):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        # gifter
        self.gifter_id: str = tags.get('msg-param-gifter-id')
        self.gifter_login: str = tags.get('msg-param-gifter-login')
        self.gifter_display_name: str = tags.get('msg-param-gifter-name')
        self.is_gifter_anon: bool = tags.get('msg-param-anon-gift') == 'true'
        # other
        self.gift_months: int = int(tags.get('msg-param-gift-months', 0))
        self.month_being_redeemed: int = int(tags.get('msg-param-gift-month-being-redeemed', 0))


class Sub(BaseSub):
    pass
#
# end of SUBS
#################################


#################################
# GIFTS
#
class BaseGift(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.is_gifter_anon = tags.get('login') == 'ananonymousgifter'
        self.plan: str = tags.get('msg-param-sub-plan')
        self.origin_id: str = unescape_tag_value(tags.get('msg-param-origin-id', ''))
        self.sender_count: int = int(tags.get('msg-param-sender-count', 0))


class SubMysteryGift(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.gift_count: int = int(tags.get('gift-count', 0))


class SubGift(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        # recipient
        self.recipient_id: str = tags.get('msg-param-recipient-id')
        self.recipient_login: str = tags.get('msg-param-recipient-user-name')
        self.recipient_display_name: str = tags.get('msg-param-recipient-display-name')
        # plan
        self.plan_name: str = unescape_tag_value(tags.get('msg-param-sub-plan-name'))
        # other
        self.months: int = int(tags.get('msg-param-months', 0))
        self.gift_months: int = int(tags.get('msg-param-gift-months', 0))
        self.fun_string: str = tags.get('msg-param-fun-string')
#
# end of GIFTS
#################################


#################################
# UPGRADES
#
class GiftPaidUpgrade(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.is_gifter_anon: bool = self.event_type == 'anongiftpaidupgrade'
        self.gifter_login: str = tags.get('msg-param-sender-login')
        self.gifter_display_name: str = tags.get('msg-param-sender-name')


class PrimePaidUpgrade(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.plan = tags.get('msg-param-sub-plan')
#
# end of UPGRADES
#################################


#################################
# PAYS FORWARD
#
class BasePayForward(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        # gifter
        self.gifter_id: str = tags.get('msg-param-prior-gifter-id')
        self.gifter_login: str = tags.get('msg-param-prior-gifter-user-name')
        self.gifter_display_name: str = tags.get('msg-param-prior-gifter-display-name')
        self.is_gifter_anon: bool = tags.get('msg-param-prior-gifter-anonymous') == 'true'


class StandardPayForward(BasePayForward):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        # recipient
        self.recipient_id: str = tags.get('msg-param-recipient-id')
        self.recipient_login: str = tags.get('msg-param-recipient-user-name')
        self.recipient_display_name: str = tags.get('msg-param-recipient-display-name')


class CommunityPayForward(BasePayForward):
    pass
#
# end of PAYS FORWARD
#################################


#################################
# RAIDS
#
class Raid(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.raider_name: str = tags.get('msg-param-displayName')
        self.raider_login: str = tags.get('msg-param-login')
        self.viewers: int = int(tags.get('msg-param-viewerCount', 0))
        self.profile_image_url: str = tags.get('msg-param-profileImageURL')


class UnRaid(BaseUserEvent):
    pass
#
# end of RAIDS
#################################


#################################
# OTHERS
#
class BitsBadgeTier(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.threshold: int = int(tags.get('msg-param-threshold', 0))


class Ritual(BaseUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.ritual_name: str = tags.get('msg-param-ritual-name')
#
# end of OTHERS
#################################
