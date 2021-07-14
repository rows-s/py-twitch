# packages
import asyncio
# from packages
from aiohttp import web
from asyncio import iscoroutinefunction
from dataclasses import dataclass
from datetime import datetime, timedelta
# project
from events import *
from exceptions import UnknownEvent, FunctionIsNotCorutine
from utils import calc_sha256, str_to_datetime
# type hints
from typing import Coroutine, Dict, Awaitable, Tuple, List, Type, Callable

__all__ = (
    'EventSub',
)


@dataclass(frozen=True)
class Event:
    handler_name: str
    spec_class: Type


@dataclass(frozen=True)
class MessageDuplicate:
    id: str
    datetime: datetime = datetime(1, 1, 1)

    def __eq__(self, other):
        return self.id == other.id
    

class EventSub:
    """ Class to handle your webhooks verifications, notifications and revocations """

    notification_events: Dict[str, Event] = {
        # 'notification_type': Event
        'channel.follow': Event('on_follow', FollowEvent),
        'channel.subscribe': Event('on_subscribe', SubscribeEvent),
        'channel.cheer': Event('on_cheer', CheerEvent),
        'channel.ban': Event('on_ban', BanEvent),
        'channel.unban': Event('on_unban', UnbanEvent),
        'stream.online': Event('on_stream_online', StreamOnlineEvent),
        'stream.offline': Event('on_stream_offline', StreamOfflineEvent),
        'user.update': Event('on_user_update', UserUpdateEvent),
        'channel.update': Event('on_channel_update', ChannelUpdateEvent),
        'channel.hype_train.begin': Event('on_hypetrain_begin', HypetrainBeginEvent),
        'channel.hype_train.progress': Event('on_hypetrain_progress', HypetrainProgressEvent),
        'channel.hype_train.end': Event('on_hypetrain_end', HypetrainEndEvent),
        'channel.channel_points_custom_reward.add': Event('on_reward_add', RewardAddEvent),
        'channel.channel_points_custom_reward.update': Event('on_reward_update', RewardUpdateEvent),
        'channel.channel_points_custom_reward.remove': Event('on_reward_remove', RewardRemoveEvent),
        'channel.channel_points_custom_reward_redemption.add': Event('on_redemption_add', RedemptionAddEvent),
        'channel.channel_points_custom_reward_redemption.update': Event('on_redemption_update', RedemptionUpdateEvent),
        'user.authorization.revoke': Event('on_authorization_revoke', AuthorizationRevokeEvent),
    }

    _events_handlers_names: Tuple[str] = (
        'on_follow', 'on_subscribe', 'on_cheer', 'on_ban', 'on_unban',  # broadcaster and user based events
        'on_stream_online', 'on_stream_offline',  # stram events
        'on_user_update', 'on_channel_update',  # update events
        'on_hypetrain_begin', 'on_hypetrain_progress', 'on_hypetrain_end',  # Hype Train events
        'on_reward_add', 'on_reward_update', 'on_reward_remove',  # rewards events
        'on_redemption_add', 'on_redemption_update',  # redemption events
        'on_authorization_revoke',  # authorization revoke
        'on_verification', 'custom_verification', 'on_revocation',  # webhook-subscription events
        'on_unknown_event'  # unknown event
    )

    def __init__(
            self,
            secret: str,
            should_verify_signature: bool = True,
            should_limit_time_range: bool = False,
            should_control_duplicates: bool = False,
            *,
            time_limit: float = 10 * 60,
            duplicates_save_period: float = 10 * 60,
            loop: asyncio.AbstractEventLoop = None
    ) -> None:
        self.secret: str = secret
        self.loop: asyncio.AbstractEventLoop = loop if loop is not None else asyncio.get_event_loop()
        # verifications
        self.disable_all_validation: bool = False
        self.should_verify_signature: bool = should_verify_signature
        # time limit
        self.should_limit_time_range: bool = should_limit_time_range
        self.time_limit = time_limit
        # duplicate control
        self.should_control_duplicates: bool = should_control_duplicates
        self.duplicates_save_period = duplicates_save_period
        self._message_duplicates: List[MessageDuplicate] = []  # would be sorted by datetime ([0]-newest, [-1]-oldest)

    @property
    def time_limit(self) -> float:
        return self._time_limit.total_seconds()

    @time_limit.setter
    def time_limit(self, value: float):
        self._time_limit: timedelta = timedelta(seconds=value)

    @property
    def duplicates_save_period(self) -> float:
        return self._duplicates_save_period.total_seconds()

    @duplicates_save_period.setter
    def duplicates_save_period(self, value: float):
        self._duplicates_save_period: timedelta = timedelta(seconds=value)

    async def handler(
            self,
            message: web.Request
    ) -> web.Response:
        # validation
        if not await self.is_message_valid(message):
            return web.HTTPBadRequest()
        # selection
        message_type = message.headers.get('Twitch-Eventsub-Message-Type')
        if message_type == 'webhook_callback_verification':
            return await self.verify_subscription(message)
        elif message_type == 'notification':
            return await self.hanlde_notification(message)
        elif message_type == 'revocation':
            return await self.handle_revocation(message)
        else:  # we don't expect anything else except verification, notification or revocation
            return web.HTTPBadRequest()

    async def is_message_valid(
            self,
            message: web.Request
    ) -> bool:
        if not self.disable_all_validation:
            message_id = message.headers.get('Twitch-Eventsub-Message-Id')
            message_datetime_str = message.headers.get('Twitch-Eventsub-Message-Timestamp')
            message_datetime = str_to_datetime(message_datetime_str, should_normalize_ms=True)
            if self.should_verify_signature:
                message_body = await message.text()
                message_sha256 = message.headers.get('Twitch-Eventsub-Message-Signature')[7:]  # removing 'sha256='
                extra_message_body = message_id + message_datetime_str + message_body
                if message_sha256 != calc_sha256(extra_message_body, key=self.secret):
                    return False
            if self.should_limit_time_range:
                if datetime.utcnow() - message_datetime > self._time_limit:
                    return False
            if self.should_control_duplicates:
                self._delete_out_of_range_duplicates()
                if MessageDuplicate(message_id) in self._message_duplicates:  # __eq__ basing on id
                    return False
                else:
                    self._save_message_to_duplicates(message)
        return True

    def _delete_out_of_range_duplicates(self):
        """ Deletes all out of range duplicates. """
        # Logic: duplicates are sorted by time ([0]-newest, [-1]-oldest)
        # so if last is not out of range - others neither, so algorithm:
        #     while duplicates not empty:
        #         if last is out of range:
        #             remove and do one more iteration
        #         else:
        #             last is in range, others are too -> break loop
        while self._message_duplicates:
            if datetime.utcnow() - self._message_duplicates[-1].datetime > self._duplicates_save_period:
                self._message_duplicates.pop()
            else:
                break

    def _save_message_to_duplicates(
            self,
            message: web.Request
    ) -> None:
        """ saves message to `self._message_duplicates` to position that matching  request's time """
        message_id = message.headers.get('Twitch-Eventsub-Message-Id')
        message_datetime_str = message.headers.get('Twitch-Eventsub-Message-Timestamp')
        message_datetime = str_to_datetime(message_datetime_str, should_normalize_ms=True)
        message = MessageDuplicate(message_id, message_datetime)
        for index, duplicate in enumerate(self._message_duplicates):
            if message.datetime > duplicate.datetime:
                self._message_duplicates.insert(index, message)  # every dupl before - newer or equal, after - later.
                break
        else:  # if list is empty, or others are later than request: current is oldest -> add to the end.
            self._message_duplicates.append(message)

    async def verify_subscription(
            self,
            message: web.Request
    ) -> web.Response:
        json = await message.json()
        webhook_sub = WebhookSubcription(json['subscription'])
        if hasattr(self, 'custom_verification'):
            try:
                is_verified = await self.custom_verification(webhook_sub)
            except:
                return web.HTTPForbidden()
            else:
                if not is_verified:
                    return web.HTTPForbidden()
        if hasattr(self, 'on_verification'):
            self._do_later(self.on_verification(webhook_sub))
        return web.Response(text=json['challenge'])

    async def hanlde_notification(
            self,
            message: web.Request
    ) -> web.Response:
        json = await message.json()
        webhook_sub = WebhookSubcription(json['subscription'])
        event_type = webhook_sub.type  # type of current notification
        try:
            event = EventSub.notification_events.get(event_type)
        except TypeError:  # None is non-iterable
            if hasattr(self, 'on_unknown_event'):
                json['headers'] = message.headers  # add headers
                self._do_later(self.on_unknown_event(json))
            return web.Response(status=200)
        else:
            if hasattr(self, event.handler_name):  # here `event_attr` is just `str` of name
                event_handler = getattr(self, event.handler_name)  # if `event_attr` exists - get the function
                raw_event = json['event']  # get raw event data
                raw_event['event_id'] = message.headers.get('Twitch-Eventsub-Message-Id')
                raw_event['event_time'] = message.headers.get('Twitch-Eventsub-Message-Timestamp')
                event = event.spec_class(raw_event)
                self._do_later(event_handler(webhook_sub, event))
            return web.Response(status=200)

    async def handle_revocation(
            self,
            message: web.Request
    ) -> web.Response:
        if hasattr(self, 'on_revocation'):
            json = await message.json()
            webhook_sub = WebhookSubcription(json['subscription'])
            self._do_later(self.on_revocation(webhook_sub))
        return web.HTTPOk()

    def event(
            self,
            coro: Coroutine
    ) -> Coroutine:
        if not iscoroutinefunction(coro):
            raise FunctionIsNotCorutine(coro.__name__)
        if coro.__name__ in EventSub._events_handlers_names:
            setattr(self, coro.__name__, coro)
        else:
            raise UnknownEvent(f'{coro.__name__} is unknown name of event')
        return coro

    def events(
            self,
            *handler_names: str
    ) -> Callable:
        def decorator(coro: Coroutine):
            if not iscoroutinefunction(coro):
                raise FunctionIsNotCorutine(coro.__name__)
            for handler_name in handler_names:
                if handler_name in EventSub._events_handlers_names:
                    setattr(self, handler_name, coro)
                else:
                    raise UnknownEvent(f'{handler_name} is unknown name of event')
        return decorator

    def _do_later(
            self,
            task: Awaitable
    ):
        """ creates task for event loop from attribute 'self.loop' """
        self.loop.create_task(task)
