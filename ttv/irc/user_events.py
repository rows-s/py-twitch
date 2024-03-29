from .messages import ChannelMessage
from .users import ChannelUser
from .channel import Channel
from .irc_messages import TwitchIRCMsg
from .emotes import Emote
from .utils import parse_raw_emotes

from abc import ABC
from typing import Tuple

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


class BaseUserEvent(ChannelMessage, ABC):
    """Base class for all user events"""
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, channel, author)
        self.system_message: str = irc_msg.get('system-msg', '')
        self.event_type: str = self.msg_id


class BaseSub(BaseUserEvent):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        # months
        self.months: int = int(irc_msg.get('msg-param-months', 0))
        self.comulative_months: int = int(irc_msg.get('msg-param-cumulative-months', 0))
        # multimonth
        self.multimonth_duration: int = int(irc_msg.get('msg-param-multimonth-duration', 0))
        self.multimonth_tenure: int = int(irc_msg.get('msg-param-multimonth-tenure', 0))
        # streak
        self.has_streak: bool = irc_msg.get('msg-param-should-share-streak') == '1'
        self.streak_months: int = int(irc_msg.get('msg-param-streak-months', 0))
        # plan
        self.plan: str = irc_msg.get('msg-param-sub-plan')
        self.plan_name: str = irc_msg.get('msg-param-sub-plan-name', '')
        # is gifted
        self.is_gifted: bool = irc_msg.get('msg-param-was-gifted') == 'true'


class ReSub(BaseSub):
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        # gifter
        self.gifter_id: str = irc_msg.get('msg-param-gifter-id')
        self.gifter_login: str = irc_msg.get('msg-param-gifter-login')
        self.gifter_display_name: str = irc_msg.get('msg-param-gifter-name')
        self.is_gifter_anon: bool = irc_msg.get('msg-param-anon-gift') == 'true'
        # other
        self.gift_months: int = int(irc_msg.get('msg-param-gift-months', 0))
        self.month_being_redeemed: int = int(irc_msg.get('msg-param-gift-month-being-redeemed', 0))


class Sub(BaseSub):
    pass


class BaseGift(BaseUserEvent):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.is_gifter_anon: bool = irc_msg.get('login') == 'ananonymousgifter'
        self.plan: str = irc_msg.get('msg-param-sub-plan')
        self.origin_id: str = irc_msg.get('msg-param-origin-id', '')
        self.sender_count: int = int(irc_msg.get('msg-param-sender-count', 0))


class SubMysteryGift(BaseUserEvent):
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.gift_count: int = int(irc_msg.get('gift-count', 0))


class SubGift(BaseUserEvent):
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        # recipient
        self.recipient_id: str = irc_msg.get('msg-param-recipient-id')
        self.recipient_login: str = irc_msg.get('msg-param-recipient-user-name')
        self.recipient_display_name: str = irc_msg.get('msg-param-recipient-display-name')
        # plan
        self.plan_name: str = irc_msg.get('msg-param-sub-plan-name')
        # other
        self.months: int = int(irc_msg.get('msg-param-months', 0))
        self.gift_months: int = int(irc_msg.get('msg-param-gift-months', 0))
        self.fun_string: str = irc_msg.get('msg-param-fun-string')


class GiftPaidUpgrade(BaseUserEvent):
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.is_gifter_anon: bool = self.event_type == 'anongiftpaidupgrade'
        self.gifter_login: str = irc_msg.get('msg-param-sender-login')
        self.gifter_display_name: str = irc_msg.get('msg-param-sender-name')


class PrimePaidUpgrade(BaseUserEvent):
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.plan = irc_msg.get('msg-param-sub-plan')


class BasePayForward(BaseUserEvent):
    def __init__(
            self, 
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        # gifter
        self.gifter_id: str = irc_msg.get('msg-param-prior-gifter-id')
        self.gifter_login: str = irc_msg.get('msg-param-prior-gifter-user-name')
        self.gifter_display_name: str = irc_msg.get('msg-param-prior-gifter-display-name')
        self.is_gifter_anon: bool = irc_msg.get('msg-param-prior-gifter-anonymous') == 'true'


class StandardPayForward(BasePayForward):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        # recipient
        self.recipient_id: str = irc_msg.get('msg-param-recipient-id')
        self.recipient_login: str = irc_msg.get('msg-param-recipient-user-name')
        self.recipient_display_name: str = irc_msg.get('msg-param-recipient-display-name')


class CommunityPayForward(BasePayForward):
    pass


class Raid(BaseUserEvent):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.raider_name: str = irc_msg.get('msg-param-displayName')
        self.raider_login: str = irc_msg.get('msg-param-login')
        self.viewers: int = int(irc_msg.get('msg-param-viewerCount', 0))
        self.profile_image_url: str = irc_msg.get('msg-param-profileImageURL')


class UnRaid(BaseUserEvent):
    pass


class BitsBadgeTier(BaseUserEvent):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.threshold: int = int(irc_msg.get('msg-param-threshold', 0))


class Ritual(BaseUserEvent):
    def __init__(
            self,
            irc_msg: TwitchIRCMsg,
            author: ChannelUser,
            channel: Channel
    ) -> None:
        super().__init__(irc_msg, author, channel)
        self.ritual_name: str = irc_msg.get('msg-param-ritual-name')
