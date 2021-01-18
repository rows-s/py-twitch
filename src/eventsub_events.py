from abc import ABC


__all__ = (
    'WebhookSubcription',
    'Transport',
    'Condition',
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


class WebhookSubcription:
    def __init__(self, raw_subscription: dict):
        self.id = raw_subscription.get('id')
        self.type = raw_subscription.get('type')
        self.version = raw_subscription.get('version')
        self.created_at = raw_subscription.get('created_at')
        # transport
        raw_transport = raw_subscription.get('transport')
        method = raw_transport.get('method')
        callback = raw_transport.get('callback')
        self.transport = Transport(method, callback)
        # cundition
        raw_condition = raw_subscription.get('condition')
        broadcaster_user_id = raw_condition.get('broadcaster_user_id')
        reward_id = raw_condition.get('reward_id')
        client_id = raw_condition.get('client_id')
        user_id = raw_condition.get('user_id')
        self.condition = Condition(broadcaster_user_id, reward_id, client_id, user_id)


class Transport:
    def __init__(self, method: str, callback: str):
        self.method: str = method
        self.callback: str = callback


class Condition:
    def __init__(self, broadcaster_user_id: str, reward_id: str, client_id: str, user_id: str):
        self.broadcaster_user_id: str = broadcaster_user_id
        self.reward_id: str = reward_id
        self.client_id: str = client_id
        self.user_id: str = user_id


#################################
# Event ABCs
#
class EventSubABC(ABC):
    """ Base class for ALL events """
    def __init__(self, raw_event: dict):
        self.event_id: str = raw_event.get('event_id')
        self.event_time: str = raw_event.get('event_time')


class BroadcasterEventABC(EventSubABC, ABC):
    """ Base class for BROADCASTER based events """
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.broadcaster_user_id: str = raw_event.get('broadcaster_user_id')
        self.broadcaster_user_login: str = raw_event.get('broadcaster_user_login')
        self.broadcaster_user_name: str = raw_event.get('broadcaster_user_name')


class UserEventABC(EventSubABC, ABC):
    """ Base class for USER based events """
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.user_id: str = raw_event.get('user_id')
        self.user_login: str = raw_event.get('user_login')
        self.user_name: str = raw_event.get('user_name')


class BroadcasterUserEventABC(BroadcasterEventABC, UserEventABC, ABC):
    """ Base class for BROADCASTER & USER based events """
    def __init__(self, raw_event: dict):
        super(BroadcasterEventABC, self).__init__(raw_event)
        super(UserEventABC, self).__init__(raw_event)
#
# end of Event ABCs
#################################


#################################
# BROADCASTER & USER based events
#
class SubscribeEvent(BroadcasterUserEventABC):
    def __init__(self, raw_event: dict):
        super(BroadcasterEventABC, self).__init__(raw_event)
        self.tier: str = raw_event.get('tier')
        self.is_gift: bool = raw_event.get('is_gift')


class CheerEvent(BroadcasterUserEventABC):
    def __init__(self, raw_event: dict):
        super(BroadcasterEventABC, self).__init__(raw_event)
        self.bits: int = raw_event.get('bits')
        self.message: str = raw_event.get('message')
        self.is_anonymous: bool = raw_event.get('is_anonymous')


class FollowEvent(BroadcasterUserEventABC):
    pass


class BanEvent(BroadcasterUserEventABC):
    pass


class UnbanEvent(BroadcasterUserEventABC):
    pass
#
# end of BROADCASTER & USER based events
#################################


#################################
# STREAM events
#
class StreamOnlineEvent(BroadcasterEventABC):
    def __init__(self, raw_event: dict):
        super(BroadcasterEventABC, self).__init__(raw_event)
        self.id: int = raw_event.get('id')
        self.type: int = raw_event.get('type')


class StreamOfflineEvent(BroadcasterEventABC):
    pass
#
# end of STREAM events
#################################


#################################
# Hype Train events
#
class HypetrainEventABC(BroadcasterEventABC, ABC):
    """ Base class for HYPE TRAIN events """
    def __init__(self, raw_event: dict):
        super(BroadcasterEventABC, self).__init__(raw_event)
        self.total: int = raw_event.get('total')
        self.started_at: str = raw_event.get('started_at')
        self.top_contributions: list = raw_event.get('top_contributions')


class HypetrainBeginEvent(HypetrainEventABC):
    def __init__(self, raw_event: dict):
        super(HypetrainEventABC, self).__init__(raw_event)
        self.progress: int = raw_event.get('progress')
        self.goal: int = raw_event.get('goal')
        self.expires_at: str = raw_event.get('expires_at')
        self.last_contribution: dict = raw_event.get('last_contribution')


class HypetrainProgressEvent(HypetrainEventABC):
    def __init__(self, raw_event: dict):
        super(HypetrainEventABC, self).__init__(raw_event)
        self.level: int = raw_event.get('level')
        self.progress: int = raw_event.get('progress')
        self.goal: int = raw_event.get('goal')
        self.expires_at: str = raw_event.get('expires_at')
        self.last_contribution: dict = raw_event.get('last_contribution')


class HypetrainEndEvent(HypetrainEventABC):
    def __init__(self, raw_event: dict):
        super(HypetrainEventABC, self).__init__(raw_event)
        self.level: int = raw_event.get('level')
        self.ended_at: str = raw_event.get('ended_at')
        self.cooldown_ends_at: str = raw_event.get('cooldown_ends_at')
#
# end of Hype Train events
#################################


#################################
# Rewards events
#
class RewardEventABC(BroadcasterEventABC, ABC):
    """ Base class for REWARD events """
    def __init__(self, event: dict):
        super(BroadcasterEventABC, self).__init__(event)
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


class RewardAddEvent(RewardEventABC):
    pass


class RewardUpdateEvent(RewardEventABC):
    pass


class RewardRemoveEvent(RewardEventABC):
    pass
#
# end of Rewards events
#################################


#################################
# Redemption events
#
class RedemptionEventABC(BroadcasterUserEventABC, ABC):
    """ Base class for reward REDEMPTION events """
    def __init__(self, event: dict):
        super(BroadcasterUserEventABC, self).__init__(event)
        self.id: str = event.get('id')
        self.user_input: str = event.get('user_input')
        self.status: str = event.get('status')
        self.reward: str = event.get('reward')
        self.redeemed_at: str = event.get('redeemed_at')


class RedemptionAddEvent(RedemptionEventABC):
    pass


class RedemptionUpdateEvent(RedemptionEventABC):
    pass
#
# end of Redemption events
#################################


#################################
# Update events
#
class ChannelUpdateEvent(BroadcasterEventABC):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.title: str = raw_event.get('title')
        self.language: str = raw_event.get('language')
        self.category_id: str = raw_event.get('category_id')
        self.category_name: str = raw_event.get('category_name')
        self.is_mature: bool = raw_event.get('is_mature')


class UserUpdateEvent(UserEventABC):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.email: int = raw_event.get('email')
        self.description: int = raw_event.get('description')
#
# end of Update events
#################################


class AuthorizationRevokeEvent(UserEventABC):
    def __init__(self, raw_event: dict):
        super().__init__(raw_event)
        self.client_id: int = raw_event.get('client_id')
