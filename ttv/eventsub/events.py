from abc import ABC


__all__ = (
    'WebhookSubscription',
    'ChannelUpdateEvent',
    'HypetrainBeginEvent',
    'HypetrainProgressEvent',
    'HypetrainEndEvent',
    'SubscribeEvent',
    'CheerEvent',
    'FollowEvent',
    'BanEvent',
    'UnbanEvent',
    'RewardAddEvent',
    'RewardUpdateEvent',
    'RewardRemoveEvent',
    'RedemptionAddEvent',
    'RedemptionUpdateEvent',
    'StreamOnlineEvent',
    'StreamOfflineEvent',
    'AuthorizationRevokeEvent',
    'UserUpdateEvent'
)


class WebhookSubscription:
    def __init__(self, raw_subscription: dict):
        self.id = raw_subscription.get('id')
        self.type = raw_subscription.get('type')
        self.status = raw_subscription.get('status')
        self.version = raw_subscription.get('version')
        self.created_at = raw_subscription.get('created_at')
        self.transport = raw_subscription.get('transport')
        self.condition = raw_subscription.get('condition')
        self.cost = raw_subscription.get('cost')


#################################
# Event ABCs
#
class BaseEvent(ABC):
    """ Base class for events """
    def __init__(self, raw_event: dict):
        self.event_id: str = raw_event.get('event_id')
        self.event_time: str = raw_event.get('event_time')


class BaseBroadcasterEvent(BaseEvent, ABC):
    """ Base class for broadcaster based events """
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.broadcaster_id: str = raw_event.get('broadcaster_user_id')
        self.broadcaster_login: str = raw_event.get('broadcaster_user_login')
        self.broadcaster_name: str = raw_event.get('broadcaster_user_name')


class BaseUserEvent(BaseEvent, ABC):
    """ Base class for user based events """
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.user_id: str = raw_event.get('user_id')
        self.user_login: str = raw_event.get('user_login')
        self.user_name: str = raw_event.get('user_name')


class SubscribeEvent(BaseBroadcasterEvent, BaseUserEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.tier: str = raw_event.get('tier')
        self.is_gift: bool = raw_event.get('is_gift')


class CheerEvent(BaseBroadcasterEvent, BaseUserEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.bits: int = raw_event.get('bits')
        self.message: str = raw_event.get('message')
        self.is_anonymous: bool = raw_event.get('is_anonymous')


class FollowEvent(BaseBroadcasterEvent, BaseUserEvent):
    pass


class BanEvent(BaseBroadcasterEvent, BaseUserEvent):
    pass


class UnbanEvent(BaseBroadcasterEvent, BaseUserEvent):
    pass


class StreamOnlineEvent(BaseBroadcasterEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.id: int = raw_event.get('id')
        self.type: int = raw_event.get('type')


class StreamOfflineEvent(BaseBroadcasterEvent):
    pass


class BaseHypetrainEvent(BaseBroadcasterEvent, ABC):
    """ Base class for hype train events """
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.total: int = raw_event.get('total')
        self.started_at: str = raw_event.get('started_at')
        self.top_contributions: list = raw_event.get('top_contributions')


class HypetrainBeginEvent(BaseHypetrainEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.progress: int = raw_event.get('progress')
        self.goal: int = raw_event.get('goal')
        self.expires_at: str = raw_event.get('expires_at')
        self.last_contribution: dict = raw_event.get('last_contribution')


class HypetrainProgressEvent(BaseHypetrainEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.level: int = raw_event.get('level')
        self.progress: int = raw_event.get('progress')
        self.goal: int = raw_event.get('goal')
        self.expires_at: str = raw_event.get('expires_at')
        self.last_contribution: dict = raw_event.get('last_contribution')


class HypetrainEndEvent(BaseHypetrainEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.level: int = raw_event.get('level')
        self.ended_at: str = raw_event.get('ended_at')
        self.cooldown_ends_at: str = raw_event.get('cooldown_ends_at')


class BaseRewardEvent(BaseBroadcasterEvent, ABC):
    """ Base class for reward events """
    def __init__(self, event: dict):
        super().__init__(event)
        self.id: str = event.get('id')
        self.title: str = event.get('title')
        self.cost: int = event.get('cost')
        self.prompt: str = event.get('prompt')
        self.background_color: str = event.get('background_color')
        self.is_enabled: bool = event.get('is_enabled')
        self.is_paused: bool = event.get('is_paused')
        self.is_in_stock: bool = event.get('is_in_stock')
        self.is_user_input_required: bool = event.get('is_user_input_required')
        self.should_redemptions_skip_request_queue: bool = event.get('should_redemptions_skip_request_queue')
        self.cooldown_expires_at: str = event.get('cooldown_expires_at')
        self.redemptions_redeemed_current_stream: str = event.get('redemptions_redeemed_current_stream')
        self.max_per_stream: dict = event.get('max_per_stream')
        self.max_per_user_per_stream: dict = event.get('max_per_user_per_stream')
        self.global_cooldown: dict = event.get('global_cooldown')
        self.default_image: dict = event.get('default_image')
        self.image: dict = event.get('image')


class RewardAddEvent(BaseRewardEvent):
    pass


class RewardUpdateEvent(BaseRewardEvent):
    pass


class RewardRemoveEvent(BaseRewardEvent):
    pass


class BaseRedemptionEvent(BaseBroadcasterEvent, BaseUserEvent, ABC):
    """ Base class for reward redemption events """
    def __init__(self, event: dict):
        super().__init__(event)
        self.id: str = event.get('id')
        self.user_input: str = event.get('user_input')
        self.status: str = event.get('status')
        self.reward: str = event.get('reward')
        self.redeemed_at: str = event.get('redeemed_at')


class RedemptionAddEvent(BaseRedemptionEvent):
    pass


class RedemptionUpdateEvent(BaseRedemptionEvent):
    pass


class ChannelUpdateEvent(BaseBroadcasterEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.title: str = raw_event.get('title')
        self.language: str = raw_event.get('language')
        self.category_id: str = raw_event.get('category_id')
        self.category_name: str = raw_event.get('category_name')
        self.is_mature: bool = raw_event.get('is_mature')


class UserUpdateEvent(BaseUserEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.email: int = raw_event.get('email')
        self.description: int = raw_event.get('description')


class AuthorizationRevokeEvent(BaseUserEvent):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.client_id: int = raw_event.get('client_id')
