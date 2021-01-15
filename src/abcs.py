from abc import ABC
from irc_channel import Channel
from irc_member import Member
from utils import replace, emotes_to_dict, badges_to_dict
from typing import Dict, List


class UserEvent(ABC):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:

        self.author: Member = author
        self.channel: Channel = channel
        self.system_msg: str = replace(tags['system-msg'])
        self.emotes: Dict[str, List[int]] = emotes_to_dict(tags['emotes'])
        self.flags: str = tags['flags']
        self.id: str = tags['id']
        self.event_type: str = tags['msg-id']
        self.time: int = int(tags['tmi-sent-ts'])
        self.content = content


class State(ABC):
    def __init__(self, tags: Dict[str, str]):
        self.badges = badges_to_dict(tags['badges'])
        self.badges_info = badges_to_dict(tags['badge-info'])


class EventSubABC(ABC):
    def __init__(self, event: dict):
        self.broadcaster_user_id: str = event.get('broadcaster_user_id')
        self.broadcaster_user_login: str = event.get('broadcaster_user_login')
        self.broadcaster_user_name: str = event.get('broadcaster_user_name')
        self.event_id: str = event.get('event_id')
        self.event_time: str = event.get('event_time')


class UserBasedEventABC(EventSubABC, ABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.user_id: str = event.get('user_id')
        self.user_login: str = event.get('user_login')
        self.user_name: str = event.get('user_name')


class OnlyUserBasedEventABC(ABC):
    def __init__(self, event: dict):
        self.user_id: str = event.get('user_id')
        self.user_login: str = event.get('user_login')
        self.user_name: str = event.get('user_name')
        self.event_id: str = event.get('event_id')
        self.event_time: str = event.get('event_time')


class RewardEventABC(EventSubABC, ABC):
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


class RedemptionEventABC(UserBasedEventABC, ABC):
    def __init__(self, event: dict):
        super().__init__(event)
        self.id: str = event.get('id')
        self.user_input: str = event.get('user_input')
        self.status: str = event.get('status')
        self.reward: str = event.get('reward')
        self.redeemed_at: str = event.get('redeemed_at')