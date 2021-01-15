import hmac
import asyncio

from time import time
from aiohttp import web
from hashlib import sha256
from datetime import datetime, timedelta
from typing import Coroutine, Dict, Awaitable, Tuple, List
from asyncio import iscoroutinefunction

import eventsub_events as types
from errors import UnknownEvent, FunctionIsNotCorutine
from utils import normalize_ms


class EventSub:
    """ Class to handle your webhooks verifications, notifications and revocations """

    _notify_events: Dict[str, Tuple[str, any]] = {  # dict of
        # 'notification_type': ('matching_attribute_name', matching_class)
        'channel.follow': ('on_follow', types.FollowEvent),
        'channel.subscribe': ('on_subscribe', types.SubscribeEvent),
        'channel.cheer': ('on_cheer', types.CheerEvent),
        'channel.ban': ('on_ban', types.BanEvent),
        'channel.unban': ('on_unban', types.UnbanEvent),
        'stream.online': ('on_stream_online', types.StreamOnlineEvent),
        'stream.offline': ('on_stream_offline', types.StreamOfflineEvent),
        'user.update': ('on_user_update', types.UserUpdateEvent),
        'channel.update': ('on_channel_update', types.ChannelUpdateEvent),
        'channel.hype_train.begin': ('on_hypetrain_begin', types.HypetrainBeginEvent),
        'channel.hype_train.progress': ('on_hypetrain_progress', types.HypetrainProgressEvent),
        'channel.hype_train.end': ('on_hypetrain_end', types.HypetrainEndEvent),
        'channel.channel_points_custom_reward.add': ('on_reward_add', types.RewardAddEvent),
        'channel.channel_points_custom_reward.update': ('on_reward_update', types.RewardUpdateEvent),
        'channel.channel_points_custom_reward.remove': ('on_reward_remove', types.RewardRemoveEvent),
        'channel.channel_points_custom_reward_redemption.add': ('on_redemption_add', types.RedemptionAddEvent),
        'channel.channel_points_custom_reward_redemption.update': ('on_redemption_update', types.RedemptionUpdateEvent),
        'user.authorization.revoke': ('on_authorization_revoke', types.AuthorizationRevokeEvent),
    }

    _event_coro_names: Tuple[str] = (
        'on_follow', 'on_subscribe', 'on_cheer', 'on_ban', 'on_unban',  # user based events
        'on_stream_online', 'on_stream_offline',  # stram events
        'on_user_update', 'on_channel_update',  # update events
        'on_hypetrain_begin', 'on_hypetrain_progress', 'on_hypetrain_end',  # Hype Train events
        'on_reward_add', 'on_reward_update', 'on_reward_remove',  # rewards events
        'on_redemption_add', 'on_redemption_update',  # redemption events
        'on_authorization_revoke',  # authorization revoke
        'on_verification', 'custom_verification', 'revocations',  # webhook-subscription events
        'on_unknown_event'  # unknown event
    )

    def __init__(
            self,
            secret: str,
            is_verify_signature: bool = True,
            is_time_limit_control: bool = False,
            is_duplicate_control: bool = False,
            *,
            time_limit: float = 10 * 60,
            duplicate_save_period: float = 10 * 60,
            is_any_verify: bool = True,
            loop: asyncio.AbstractEventLoop = None
    ) -> None:
        self._secret: str = secret
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        # verifications
        self.is_any_verify: bool = is_any_verify
        # verify_signature
        self.is_verify_signature: bool = is_verify_signature
        # time limit
        self.is_time_limit_control: bool = is_time_limit_control
        self.time_limit: timedelta = timedelta(seconds=time_limit)
        # duplicate control
        self.is_duplicate_control: bool = is_duplicate_control
        self.duplicate_save_period: timedelta = timedelta(seconds=duplicate_save_period)
        self._duplicates: List[Tuple[str, datetime]] = []  # list with (duplicate_id, duplicate_time) !SORTED BY TIME!

    async def handle(
            self,
            request: web.BaseRequest
    ) -> web.Response:
        handling_start_time = time()
        request_type = request.headers.get('Twitch-Eventsub-Message-Type')
        request_id = request.headers.get('Twitch-Eventsub-Message-Id')
        request_time = request.headers.get('Twitch-Eventsub-Message-Timestamp')

        if self.is_any_verify:
            if self.is_verify_signature:
                request_body = await request.text()
                request_sha256 = request.headers.get('Twitch-Eventsub-Message-Signature')[7:]  # remove 'sha256='
                text_to_sha256 = request_id + request_time + request_body
                if request_sha256 != self.calc_sha256(text_to_sha256, key=self._secret):
                    return web.HTTPBadRequest()

            if self.is_time_limit_control:
                request_datetime = self.str_to_datatime(request_time, normalize=True)
                if (datetime.utcnow() - request_datetime) > self.time_limit:
                    return web.Response(status=200)

            if self.is_duplicate_control:
                self._delete_outrange_duplicates()

                request_datetime = self.str_to_datatime(request_time, normalize=True)
                if (request_id, request_datetime) in reversed(self._duplicates):
                    return web.Response(status=200)

                self._save_duplicate(request_id, request_datetime)

        json = await request.json()
        wh_sub = types.WebhookSubcription(json['subscription'])

        if request_type == 'webhook_callback_verification':
            json = await request.json()

            if hasattr(self, 'custom_verification'):
                is_verified = await self.custom_verification(wh_sub, json['challenge'])
                if is_verified:
                    return web.Response(text=json['challenge'])
                else:
                    return web.HTTPForbidden()

            if hasattr(self, 'on_verification'):
                self._do_later(self.on_verification(wh_sub, json['challenge']))
            print('is verify', time() - handling_start_time)
            return web.Response(text=json['challenge'])

        elif request_type == 'notification':
            event_type = wh_sub.type  # type of current notification
            try:
                event_attr, event_class = EventSub._notify_events.get(event_type)
            except TypeError:  # None is non-iterable
                if hasattr(self, 'on_unknown_event'):
                    json['headers'] = request.headers  # add headers
                    self._do_later(self.on_unknown_event(json))
                print('unknown event', time() - handling_start_time)
                return web.Response(status=200)
            else:
                if hasattr(self, event_attr):  # here `event_attr` is just str of name
                    event_handler = getattr(self, event_attr)  # if `event_attr` exists - get the function
                    raw_event = json['event']  # get raw event data
                    raw_event['event_id'] = request_id  # add id of current event
                    raw_event['event_time'] = request_time  # add time of current event
                    event = event_class(raw_event)  # create `event` as object of matching class
                    self._do_later(event_handler(wh_sub, event))  # send to do later
                    print('_do_later', event_attr, time() - handling_start_time)
                else:  # else - current `self` is not handler for current event
                    print('not registred event', time() - handling_start_time)
                return web.Response(status=200)

        elif request_type == 'revocation':
            if hasattr(self, 'on_revocation'):
                self._do_later(self.on_revocation(wh_sub))

        else:  # we don't wait nothing else except verification, notification and revocation
            return web.HTTPBadRequest()

    def event(self, coro: Coroutine) -> Coroutine:
        if not iscoroutinefunction(coro):
            raise FunctionIsNotCorutine(coro.__name__)
        if coro.__name__ in EventSub._event_coro_names:
            setattr(self, coro.__name__, coro)
        else:
            raise UnknownEvent(f'{coro.__name__} is unknown name of event')
        return coro

    def _delete_outrange_duplicates(self):
        """
        Deletes all out of range duplicates.

        -------------------

        Returns:
        ==================
            None
        ------------------

        Notes:
        ==================
            Logic: because duplicates are sorted by time, we know:
                1) if first is not out of range - others neither
                so we whole times check only first:
                    if it out of range:
                        delete and one more iteration
                    else:
                        others neither - stop loop
        ------------------
        """
        while len(self._duplicates):
            duplicate_time = self._duplicates[0][1]
            if datetime.utcnow() - duplicate_time > self.duplicate_save_period:
                self._duplicates.pop(0)
                continue
            else:
                break

    def _save_duplicate(self, request_id: str, request_datetime: datetime):
        """
        saves duplicate in position that matching  request's time

        -------------

        Args:
        =============
            request_id: `str`
                id of request

            request_datetime: :class:`datetime`
                time of request
        ------------

        Returns:
        ============
            None
        ------------
        """
        index = len(self._duplicates)  # iterator is reversed - so index to inserting is last
        for _, duplicate_time in reversed(self._duplicates):  # more of request will be latest or close to
            if request_datetime > duplicate_time:  # if later than current duplicate - insert and break, else- look next
                self._duplicates.insert(index, (request_id, request_datetime))
                break
        else:  # if list is empty, or others is later then request - index is 0
            self._duplicates.insert(0, (request_id, request_datetime))

    @staticmethod
    def calc_sha256(
            text: str,
            key: str,
    ) -> str:
        text_bytes = bytes(text, 'utf-8')
        key_bytes = bytes(key, 'utf-8')
        signature = hmac.new(key_bytes, text_bytes, sha256).hexdigest()
        return signature

    @staticmethod
    def str_to_datatime(date: str, normalize: bool = True) -> datetime:
        if normalize:
            date = normalize_ms(date)
        return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')

    def _do_later(self, func: Awaitable):
        self.loop.create_task(func)
