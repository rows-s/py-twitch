import abcs


__all__ = [
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
]


class WebhookSubcription:
    def __init__(self, sub_dict: dict):
        self.id = sub_dict.get('id')
        self.type = sub_dict.get('type')
        self.version = sub_dict.get('version')
        self.created_at = sub_dict.get('created_at')

        method = sub_dict.get('transport').get('method')
        callback = sub_dict.get('transport').get('callback')
        self.transport = Transport(method, callback)

        broadcaster_user_id = sub_dict.get('condition').get('broadcaster_user_id')
        reward_id = sub_dict.get('condition').get('reward_id')
        client_id = sub_dict.get('condition').get('client_id')
        user_id = sub_dict.get('condition').get('user_id')
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


class ChannelUpdateEvent(abcs.EventSubABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.title: str = event.get('title')
        self.language: str = event.get('language')
        self.category_id: str = event.get('category_id')
        self.category_name: str = event.get('category_name')
        self.is_mature: bool = event.get('is_mature')


class HypetrainBeginEvent(abcs.EventSubABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.total: int = event.get('total')
        self.progress: int = event.get('progress')
        self.goal: int = event.get('goal')
        self.started_at: str = event.get('started_at')
        self.expires_at: str = event.get('expires_at')
        self.top_contributions: list = event.get('top_contributions')
        self.last_contribution: dict = event.get('last_contribution')


class HypetrainProgressEvent(abcs.EventSubABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.level: int = event.get('level')
        self.total: int = event.get('total')
        self.progress: int = event.get('progress')
        self.goal: int = event.get('goal')
        self.started_at: str = event.get('started_at')
        self.expires_at: str = event.get('expires_at')
        self.top_contributions: list = event.get('top_contributions')
        self.last_contribution: dict = event.get('last_contribution')


class HypetrainEndEvent(abcs.EventSubABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.level: int = event.get('level')
        self.total: int = event.get('total')
        self.started_at: str = event.get('started_at')
        self.ended_at: str = event.get('ended_at')
        self.cooldown_ends_at: str = event.get('cooldown_ends_at')
        self.top_contributions: list = event.get('top_contributions')


class SubscribeEvent(abcs.UserBasedEventABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.tier: str = event.get('tier')
        self.is_gift: bool = event.get('is_gift')


class CheerEvent(abcs.UserBasedEventABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.bits: int = event.get('bits')
        self.message: str = event.get('message')
        self.is_anonymous: bool = event.get('is_anonymous')


class FollowEvent(abcs.UserBasedEventABC):
    pass


class BanEvent(abcs.UserBasedEventABC):
    pass


class UnbanEvent(abcs.UserBasedEventABC):
    pass


class RewardAddEvent(abcs.RewardEventABC):
    pass


class RewardUpdateEvent(abcs.RewardEventABC):
    pass


class RewardRemoveEvent(abcs.RewardEventABC):
    pass


class RedemptionAddEvent(abcs.RedemptionEventABC):
    pass


class RedemptionUpdateEvent(abcs.RedemptionEventABC):
    pass


class StreamOnlineEvent(abcs.EventSubABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.id: int = event.get('id')
        self.type: int = event.get('type')


class StreamOfflineEvent(abcs.EventSubABC):
    pass


class AuthorizationRevokeEvent(abcs.OnlyUserBasedEventABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.client_id: int = event.get('client_id')


class UserUpdateEvent(abcs.OnlyUserBasedEventABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.email: int = event.get('email')
        self.description: int = event.get('description')
