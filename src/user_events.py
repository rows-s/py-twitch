from abc import ABC
from typing import Dict, Optional
from utils import replace
from member import Member
from channel import Channel
from abcs import UserEvent


class Sub(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:

        super().__init__(author, channel, tags, content)
        self.comulative_months: int = int(tags['msg-param-cumulative-months'])
        self.months_duration: int = int(tags['msg-param-multimonth-duration'])
        self.months_tenure: int = int(tags['msg-param-multimonth-tenure'])
        self.share_streak: bool = bool(int(tags['msg-param-should-share-streak']))
        if self.share_streak:
            self.streak: Optional[int] = int(tags['msg-param-streak-months'])
        else:
            self.streak = None
        self.gifted: bool = True if (tags['msg-param-was-gifted'] == 'true') else False
        self.plan: str = tags['msg-param-sub-plan']
        self.plan_name: str = replace(tags['msg-param-sub-plan-name'])


class SubGift(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.gift_id: str = replace(tags['msg-param-origin-id'])
        self.gift_months = int(tags['msg-param-gift-months'])
        self.months: int = int(tags['msg-param-months'])
        self.recipient_name: Optional[str] = tags['msg-param-recipient-display-name']
        self.recipient_id: Optional[str] = tags['msg-param-recipient-id']
        self.plan_name: str = replace(tags['msg-param-sub-plan-name'])
        self.plan: str = tags['msg-param-sub-plan']


class GiftPaidUpgrade(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.gift_total: Optional[int] = tags.get('msg-param-promo-gift-total')
        if self.gift_total is not None: self.gift_total = int(self.gift_total)

        self.promo_name: Optional[str] = tags.get('msg-param-promo-name')
        self.gifter_name: Optional[str] = tags.get('msg-param-sender-name')


class Ritual(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.ritual_name: str = tags['msg-param-ritual-name']


class BitsBadgeTier(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.threshold: int = int(tags['msg-param-threshold'])


class Raid(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.raider_name: str = tags['msg-param-displayName']
        self.viewers: int = int(tags['msg-param-viewerCount'])
        self.avatar: str = tags['msg-param-profileImageURL']


class UnRaid(UserEvent):
    pass


class SubMysteryGift(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.gift_count: int = int(tags['msg-param-mass-gift-count'])
        self.gift_id: str = replace(tags['msg-param-origin-id'])
        self.plan: str = tags['msg-param-sub-plan']

        self.sender_count: Optional[int] = tags.get('msg-param-sender-count')
        if self.sender_count is not None:
            self.sender_count = int(self.sender_count)


class RewardGift(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.domain: str = tags['msg-param-domain']
        self.selected_count: int = int(tags['msg-param-selected-count'])
        self.total_reward_count: int = int(tags['msg-param-total-reward-count'])
        self.trigger_amount: int = int(tags['msg-param-trigger-amount'])
        self.trigger_type: str = tags['msg-param-trigger-type']


class CommunityPayForward(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.gifter_anon: bool = True if tags['msg-param-prior-gifter-anonymous'] == 'true' else False
        self.gifter_name: str = tags['msg-param-prior-gifter-display-name']
        self.gifter_id: int = int(tags['msg-param-prior-gifter-id'])


class PrimePaidUpgrade(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.plan = tags['msg-param-sub-plan']


class StandardPayForward(UserEvent):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:
        super().__init__(author, channel, tags, content)
        self.gifter_anon: bool = True if tags['msg-param-prior-gifter-anonymous'] == 'true' else False
        self.gifter_id: int = int(tags['msg-param-prior-gifter-id'])
        self.gifter_name: str = tags['msg-param-prior-gifter-display-name']
        self.recipient_id: int = int(tags['msg-param-recipient-id'])
        self.recipient_name: str = tags['msg-param-recipient-display-name']
