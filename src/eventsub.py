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
    """
    Class to handle your webhooks verifications, notifications and revocations.
    """

    _notify_events: Dict[str, Tuple[str, any]] = {  # dict of
        # 'event_type': ('matching_attribute_name', matching_class)
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
        'on_verification', 'revocations',  # webhook-subscription events
        'on_unknown_event'  # unknown event
    )

    def __init__(
            self,
            secret: str,
            verify_signature: bool = True,
            check_time_limit: bool = False,
            duplicate_control: bool = False,
            *,
            time_limit: int = 10 * 60,
            duplicate_save_time: int = 10 * 60,
            any_verify: bool = True,
            loop: asyncio.AbstractEventLoop = None
    ) -> None:
        self._secret: str = secret
        self.any_verify = any_verify
        self.verify_signature: bool = verify_signature
        self.check_time_limit: bool = check_time_limit
        self.time_limit: timedelta = timedelta(seconds=time_limit)
        self.duplicate_control: bool = duplicate_control
        self.duplicate_save_period: timedelta = timedelta(seconds=duplicate_save_time)
        self._duplicates: List[Tuple[str, datetime]] = []
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop

    async def handler(
            self,
            request: web.BaseRequest
    ) -> web.Response:
        t0 = time()
        req_type = request.headers.get('Twitch-Eventsub-Message-Type')
        req_id = request.headers.get('Twitch-Eventsub-Message-Id')
        req_time = request.headers.get('Twitch-Eventsub-Message-Timestamp')
        if self.any_verify:
            if self.verify_signature:
                req_body = await request.text()
                req_signature = request.headers.get('Twitch-Eventsub-Message-Signature')
                if req_signature[7:] != self.calc_sign(req_id + req_time + req_body, key=self._secret):
                    print('bad sign', time() - t0)
                    return web.HTTPBadRequest()

            if self.check_time_limit:
                req_datetime = self.to_datatime(req_time, normalize=True)
                if datetime.utcnow() - req_datetime > self.time_limit:
                    print('bad time', time() - t0)
                    return web.Response(status=200)

            if self.duplicate_control:
                for dupl_id, dupl_time in self._duplicates:  # loop for delete all out of range duplicates
                    if datetime.utcnow() - dupl_time > self.duplicate_save_period:
                        self._duplicates.pop()
                        continue  # logic: dupls are sorted by time, so if first is not out of range - others neither,
                    break  # so if first is out of range - one more iteration, else - break the loop

                # we use reversed list, cuz in more of cases dupl will be in the end, so `current_indx` must be latest
                # `current_indx` is index of current request in the list sorted by time
                current_indx = len(self._duplicates)
                found_current_indx = False
                req_datetime = self.to_datatime(req_time, normalize=True)
                for dupl_id, dupl_time in reversed(self._duplicates):  # loop for find equal duplicate
                    if dupl_id == req_id:  # if have dupl - return 200-status (stop current handling)
                        print('is dupl', time() - t0)
                        return web.Response(status=200)
                    if not found_current_indx:  # if we've "found current indx" we don't need to check anymore
                        if req_datetime > dupl_time:  # if current request is later than `dupl_time` - save index
                            found_current_indx = True  # and mark that we found it
                        else:  # else - keep looking with next index
                            current_indx -= 1  # decrement the index (cuz the iteration is reversed)
                else:  # if duplicate has been not found - save in `self._duplicates` with matching index
                    self._duplicates.insert(current_indx, (req_id, req_datetime))

        json = await request.json()
        wh_sub = types.WebhookSubcription(json['subscription'])

        if req_type == 'webhook_callback_verification':  # if webhook verification
            json = await request.json()
            if hasattr(self, 'on_verification'):
                self._do_later(self.on_verification(wh_sub, json['challenge']))
            print('is verify', time() - t0)
            return web.Response(text=json['challenge'])

        elif req_type == 'notification':  # if notification
            event_type = wh_sub.type  # type of current notification
            attr_and_class = EventSub._notify_events.get(event_type)  # attr and class that match `event_type`
            if attr_and_class is not None:  # if got tuple
                event_attr, event_class = attr_and_class
                if hasattr(self, event_attr):  # here `event_attr` is just str of name
                    event_handler = getattr(self, event_attr)  # if `attr` exists - get the function
                    raw_event = json['event']  # get raw event data
                    raw_event['event_id'] = req_id  # add id of current event
                    raw_event['event_time'] = req_time  # add time of current event
                    event = event_class(raw_event)  # create `event` as object of matching class
                    self._do_later(event_handler(wh_sub, event))  # send to do later
                    print('_do_later', event_attr, time() - t0)
                else:  # else - current `self` is not to handle current event
                    print('not registred event', time() - t0)
                return web.Response(status=200)
            else:  # else - unknown event
                if hasattr(self, 'on_unknown_event'):
                    json['headers'] = request.headers  # add headers
                    self._do_later(self.on_unknown_event(json))
                print('unknown event', time() - t0)
                return web.Response(status=200)
        elif req_type == 'revocation':
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

    @staticmethod
    def calc_sign(
            text: str,
            key: str,
    ) -> str:
        text_bytes = bytes(text, 'utf-8')
        key_bytes = bytes(key, 'utf-8')
        signature = hmac.new(key_bytes, text_bytes, sha256).hexdigest()
        return signature

    @staticmethod
    def to_datatime(date: str, normalize: bool = True) -> datetime:
        if normalize:
            date = normalize_ms(date)
        return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')

    def _do_later(self, func: Awaitable):
        self.loop.create_task(func)
