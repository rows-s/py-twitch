from irc_users import ChannelMember
from irc_channel import Channel
from utils import replace_slashes
from irc_messages import ChannelMessage

from typing import Dict


class AbstractUserEvent(ChannelMessage):
    """ Base class for all IRC user events """
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(channel, author, content, tags)
        self.system_message: str = replace_slashes(tags.get('system-msg', ''))
        self.event_type: str = tags.get('msg-id')


#################################
# SUBS
#
class AbstractSub(AbstractUserEvent):
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
        self.plan_name: str = replace_slashes(tags.get('msg-param-sub-plan-name', ''))
        # is gifted
        self.is_gifted: bool = tags.get('msg-param-was-gifted') == 'true'


class ReSub(AbstractSub):
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


class Sub(AbstractSub):
    pass
#
# end of SUBS
#################################


#################################
# GIFTS
#
class AbstractGift(AbstractUserEvent):
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
        self.origin_id: str = replace_slashes(tags.get('msg-param-origin-id', ''))
        self.sender_count: int = int(tags.get('msg-param-sender-count', 0))


class SubMysteryGift(AbstractUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.gift_count: int = int(tags.get('gift-count', 0))


class SubGift(AbstractUserEvent):
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
        self.plan_name: str = replace_slashes(tags.get('msg-param-sub-plan-name'))
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
class GiftPaidUpgrade(AbstractUserEvent):
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


class PrimePaidUpgrade(AbstractUserEvent):
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
class AbstractPayForward(AbstractUserEvent):
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


class StandardPayForward(AbstractPayForward):
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


class CommunityPayForward(AbstractPayForward):
    pass
#
# end of PAYS FORWARD
#################################


#################################
# OTHERS
#
class BitsBadgeTier(AbstractUserEvent):
    def __init__(
            self,
            author: ChannelMember,
            channel: Channel,
            content: str,
            tags: Dict[str, str]
    ) -> None:
        super().__init__(author, channel, content, tags)
        self.threshold: int = int(tags.get('msg-param-threshold', 0))


class Ritual(AbstractUserEvent):
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


#################################
# RAIDS
#
class Raid(AbstractUserEvent):
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


class UnRaid(AbstractUserEvent):
    pass
#
# end of RAIDS
#################################
