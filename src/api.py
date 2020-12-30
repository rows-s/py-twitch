

import aiohttp

from errors import HTTPError, InvalidToken, WrongIterObjects
from utils import insert_params

from typing import Dict, Any, Union, Iterable, List

_Bool = Union[bool, str]
_Int = Union[int, str]
_IntIter = Union[Iterable[Union[int, str]], int, str]
_StrIter = Union[Iterable[str], str]
_Data = Dict[str, Union[str, int, bool]]
_Params = Dict[str, Union[Iterable[Union[int, str]], int, str, bool]]


class Api:
    def __init__(self):
        self._headers = {}
        self._scopes = []

    async def set_auth(self, auth: str):
        headers = {'Authorization': 'Bearer ' + auth}
        url = 'https://id.twitch.tv/oauth2/validate?'
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                json = await response.json()
                if response.status == 401:
                    raise InvalidToken(json)
                headers['Client-Id'] = json['client_id']
                self._scopes = json['scopes']
                self._headers = headers

    async def start_commercial(self, data: _Data = None, *,
                               broadcaster_id: _Int = None,
                               length: _Int = None):
        url = 'https://api.twitch.tv/helix/channels/commercial?'
        if data is None:
            data = {'broadcaster_id': broadcaster_id, 'length': length}

        if data.get('broadcaster_id') is None:
            raise TypeError('`broadcaster_id` must be not None')
        if data.get('length') is None:
            raise TypeError('`length` must be not None')
        elif str(data['length']) not in ['30', '60', '90', '120', '150', '180']:
            raise TypeError('`length` must be one of following values: 30, 60, 90, 120, 150, 180')

        response = await self._http_post(url, data)
        return response['data']

    async def get_extension_analytics(self, limit: int, params: _Params = None, *,
                                      extension_id: str = None,
                                      started_at: str = None,
                                      ended_at: str = None,
                                      type: str = None):
        url = 'https://api.twitch.tv/helix/analytics/extensions?'
        if params is None:
            params = {}
            if extension_id: params['extension_id'] = extension_id
            if started_at: params['started_at'] = started_at
            if ended_at: params['ended_at'] = ended_at
            if type: params['type'] = type

        if params.get('type') is not None:
            if params['type'] not in ['overview_v1', 'overview_v2']:
                TypeError('`type` must be one of following strings: "overview_v1", "overview_v2"')

        url = insert_params(url, limit, params)
        async for extension in self.to_be_continue(url, limit):
            yield extension

    async def get_game_analytics(self, limit: int, params: _Params = None, *,
                                 game_id: _Int = None,
                                 started_at: str = None,
                                 ended_at: str = None,
                                 type: str = None):
        url = 'https://api.twitch.tv/helix/analytics/games?'
        if params is None:
            params = {}
            if game_id: params['game_id'] = game_id
            if started_at: params['started_at'] = started_at
            if ended_at: params['ended_at'] = ended_at
            if type: params['type'] = type

        url = insert_params(url, limit, params)
        async for game in self.to_be_continue(url, limit):
            yield game

    async def get_bits_leaderboard(self, limit: int, params: _Params = None, *,
                                   count: _Int = None,
                                   period: str = None,
                                   started_at: str = None,
                                   user_id: _Int = None):
        url = 'https://api.twitch.tv/helix/bits/leaderboard?'
        if params is None:
            params = {}
            if count: params['count'] = count
            if started_at: params['started_at'] = started_at
            if period: params['period'] = period
            if user_id: params['user_id'] = user_id

        try:  # this request doesn't contain `first` parameter, only count
            params['count'] = max(limit, params['count'])
        except KeyError:  # if `params['count']` is None
            params['count'] = limit
        finally:  # and this parameter has limited value - 100
            limit = params['count'] = min(100, params['count'])

        if params.get('period') is not None:
            if params['period'] not in ['day', 'week', 'month', 'year', 'all']:
                TypeError('`period` must be one of following strings: "day", "week", "month", "year", "all"')

        url = insert_params(url, 0, params)
        async for leader in self.to_be_continue(url, limit):
            yield leader

    async def get_cheermotes(self, limit: int, broadcaster_id: _Int):
        url = 'https://api.twitch.tv/helix/analytics/games?'
        url = insert_params(url, 0, {'broadcaster_id': broadcaster_id})
        async for cheermote in self.to_be_continue(url, limit):
            yield cheermote

    async def get_extension_transactions(self, limit: int, params: _Params = None, *,
                                         extension_id: _Int = None,
                                         traransaction_id: _StrIter = None):
        url = 'https://api.twitch.tv/helix/extensions/transactions?'
        if params is None:
            params = {'extension_id': extension_id}
            if traransaction_id:
                params['id'] = extension_id
        else:
            traransaction_id = params.pop('traransaction_id', None)
            if traransaction_id is not None:
                params['id'] = traransaction_id

        if params.get('extension_id') is None:
            raise TypeError('`extension_id`(`id`) must be not None')

        url = insert_params(url, limit, params)
        async for transaction in self.to_be_continue(url, limit):
            yield transaction

    async def create_custom_rewards(self, data: _Data = None, *,
                                    broadcaster_id: _Int = None,
                                    title: str = None,
                                    cost: _Int = None,
                                    prompt: str = None,
                                    is_enabled: _Bool = None,
                                    max_per_stream: _Int = None,
                                    background_color: str = None,
                                    is_user_input_required: _Bool = None,
                                    max_per_user_per_stream: _Int = None,
                                    global_cooldown_seconds: _Int = None,
                                    is_max_per_stream_enabled: _Bool = None,
                                    is_global_cooldown_enabled: _Bool = None,
                                    is_max_per_user_per_stream_enabled: _Bool = None,
                                    should_redemptions_skip_request_queue: _Bool = None):
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards?'
        if data is None:
            data = {'cost': cost, 'title': title}
            if prompt: data['prompt'] = prompt
            if is_enabled: data['is_enabled'] = is_enabled
            if max_per_stream: data['max_per_stream'] = max_per_stream
            if background_color: data['background_color'] = background_color
            if is_user_input_required: data['is_user_input_required'] = is_user_input_required
            if max_per_user_per_stream: data['max_per_user_per_stream'] = max_per_user_per_stream
            if global_cooldown_seconds: data['global_cooldown_seconds'] = global_cooldown_seconds
            if is_max_per_stream_enabled: data['is_max_per_stream_enabled'] = is_max_per_stream_enabled
            if is_global_cooldown_enabled: data['is_global_cooldown_enabled'] = is_global_cooldown_enabled
            if is_max_per_user_per_stream_enabled:
                data['is_max_per_user_per_stream_enabled'] = is_max_per_user_per_stream_enabled
            if should_redemptions_skip_request_queue:
                data['should_redemptions_skip_request_queue'] = should_redemptions_skip_request_queue

        if data.get('title') is None:
            raise TypeError('`title`must be not None')
        if data.get('cost') is None:
            raise TypeError('`cost` must be not None')
        if broadcaster_id is None:
            broadcaster_id = data.pop('broadcaster_id', None)
            if broadcaster_id is None:
                raise TypeError('`broadcaster_id` must be not None')

        url = insert_params(url, 0, {'broadcaster_id': broadcaster_id})
        response = await self._http_post(url, data)
        return response['data']

    async def delete_custom_reward(self, params: _Params = None, *,
                                   broadcaster_id: _Int = None,
                                   reward_id: str = None):
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards?'
        if params is None:
            params = {'broadcaster_id': broadcaster_id,
                      'id': reward_id}
        else:
            reward_id = params.pop('reward_id', None)
            if reward_id is not None:
                params['id'] = reward_id

        if params.get('broadcaster_id') is None:
            raise TypeError('`broadcaster_id` must be not None')
        if params.get('id') is None:
            raise TypeError('`reward_id`(`id`) must be not None')

        url = insert_params(url, 0, params)
        return await self._http_delete(url)

    async def get_custom_reward(self, limit: int, params: _Params = None, *,
                                broadcaster_id: _Int = None,
                                reward_id: _StrIter = None,
                                only_manageable_rewards: _Bool = None):
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards?'
        if params is None:
            params = {'broadcaster_id': broadcaster_id}
            if reward_id: params['id'] = reward_id
            if only_manageable_rewards: params['only_manageable_rewards'] = only_manageable_rewards
        else:
            reward_id = params.pop('reward_id', None)
            if reward_id is not None:
                params['id'] = reward_id

        if params.get('broadcaster_id') is None:
            raise TypeError('`broadcaster_id` must be not None')

        url = insert_params(url, 0, params)
        async for reward in self.to_be_continue(url, limit):
            yield reward

    async def get_custom_reward_redemption(self, limit: int, params: _Params = None, *,
                                           broadcaster_id: _Int = None,
                                           reward_id: str = None,
                                           id: _StrIter = None,
                                           status: str = None,
                                           sort: str = None):
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions?'
        if params is None:
            params = {'broadcaster_id': broadcaster_id, 'reward_id': reward_id}
            if id: params['id'] = id
            if sort: params['sort'] = sort
            if status: params['status'] = status

        status = params.get('status')
        if status is not None:
            if status not in ['UNFULFILLED', 'FULFILLED', 'CANCELED']:
                raise TypeError('`status` must be one of following stings: "UNFULFILLED" or "FULFILLED" or "CANCELED"')
        sort = params.get('sort')
        if sort is not None:
            if sort not in ['OLDEST', 'NEWEST']:
                raise TypeError('`sort` must be one of following stings: "OLDEST" or "NEWEST"')
        if params.get('broadcaster_id') is None:
            raise TypeError('`broadcaster_id` must be not None')
        if params.get('reward_id') is None:
            raise TypeError('`reward_id` must be not None')

        url = insert_params(url, min(limit, 50), params)  # `first` limit is 50 for this request
        async for reward in self.to_be_continue(url, limit):
            yield reward

    async def update_custom_reward(self, data: _Data = None, *,
                                   broadcaster_id: _Int = None,
                                   reward_id: str = None,
                                   title: str = None,
                                   cost: _Int = None,
                                   prompt: str = None,
                                   is_paused: _Bool = None,
                                   is_enabled: _Bool = None,
                                   max_per_stream: _Int = None,
                                   background_color: str = None,
                                   is_user_input_required: _Bool = None,
                                   max_per_user_per_stream: _Int = None,
                                   global_cooldown_seconds: _Int = None,
                                   is_max_per_stream_enabled: _Bool = None,
                                   is_global_cooldown_enabled: _Bool = None,
                                   is_max_per_user_per_stream_enabled: _Bool = None,
                                   should_redemptions_skip_request_queue: _Bool = None):
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards?'
        if data is None:
            data = {}
            if cost: data['cost'] = cost
            if title: data['title'] = title
            if prompt: data['prompt'] = prompt
            if is_paused: data['is_paused'] = is_paused
            if is_enabled: data['is_enabled'] = is_enabled
            if max_per_stream: data['max_per_stream'] = max_per_stream
            if background_color: data['background_color'] = background_color
            if is_user_input_required: data['is_user_input_required'] = is_user_input_required
            if max_per_user_per_stream: data['max_per_user_per_stream'] = max_per_user_per_stream
            if global_cooldown_seconds: data['global_cooldown_seconds'] = global_cooldown_seconds
            if is_max_per_stream_enabled: data['is_max_per_stream_enabled'] = is_max_per_stream_enabled
            if is_global_cooldown_enabled: data['is_global_cooldown_enabled'] = is_global_cooldown_enabled
            if is_max_per_user_per_stream_enabled:
                data['is_max_per_user_per_stream_enabled'] = is_max_per_user_per_stream_enabled
            if should_redemptions_skip_request_queue:
                data['should_redemptions_skip_request_queue'] = should_redemptions_skip_request_queue

        if broadcaster_id is None:
            broadcaster_id = data.pop('broadcaster_id', None)
            if broadcaster_id is None:
                raise TypeError('`broadcaster_id` must be not None')
        if reward_id is None:
            reward_id = data.pop('reward_id', None)
            if reward_id is None:
                reward_id = data.pop('id', None)
                if reward_id is None:
                    raise TypeError('`reward_id` must be not None')

        url = insert_params(url, 0, {'broadcaster_id': broadcaster_id, 'id': reward_id})
        response = await self._http_patch(url, data)
        return response['data']

    async def update_redemption_status(self, data: _Data = None, *,
                                       broadcaster_id: _Int = None,
                                       reward_id: str = None,
                                       id: _StrIter = None,
                                       status: str = None):
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions?'
        if data is None:
            data = {'status': status}

        if broadcaster_id is None:
            broadcaster_id = data.pop('broadcaster_id', None)
            if broadcaster_id is None:
                raise TypeError('`broadcaster_id` must be not None')
        if reward_id is None:
            reward_id = data.pop('reward_id', None)
            if reward_id is None:
                raise TypeError('`reward_id` must be not None')
        if id is None:
            id = data.pop('id', None)
            if id is None:
                raise TypeError('`id` must be not None')
        if data.get('status') is not None:
            if data['status'] not in ['UNFULFILLED', 'CANCELED']:
                raise TypeError('`status` must be one of following strings: "UNFULFILLED" or "CANCELED"')
        else:
            raise TypeError('`status` must be one of following strings: "UNFULFILLED" or "CANCELED"')

        url = insert_params(url, 0, {'broadcaster_id': broadcaster_id, 'reward_id': reward_id, 'id': id})
        response = await self._http_patch(url, data)
        return response['data']

    async def create_clip(self, params: _Params = None, *,
                          broadcaster_id: _Int = None,
                          has_delay: _Bool = None):
        url = 'https://api.twitch.tv/helix/clips?'
        if params is None:
            params = {'broadcaster_id': broadcaster_id}
            if has_delay is not None:
                params['has_delay'] = has_delay

        if params['broadcaster_id'] is None:
            raise TypeError('`broadcaster_id` must be not None')

        url = insert_params(url, 0, params)
        response = await self._http_post(url, {})
        return response['data']

    async def get_clips(self, limit: int, params: _Params = None, *,
                        broadcaster_id: _Int = None,
                        game_id: _Int = None,
                        clip_id: _StrIter = None,
                        started_at: str = None,
                        ended_at: str = None):
        url = 'https://api.twitch.tv/helix/clips?'
        if params is None:
            params = {}
            if broadcaster_id: params['broadcaster_id'] = broadcaster_id
            if game_id: params['game_id'] = game_id
            if clip_id: params['id'] = clip_id
            if started_at: params['started_at'] = started_at
            if ended_at: params['ended_at'] = ended_at

        if params['broadcaster_id'] is None and params['game_id'] is None and params['clip_id'] is None:
            raise TypeError('One of following args must be not None: `broadcaster_id` or `game_id` or `clip_id`')

        url = insert_params(url, limit, params)
        async for clip in self.to_be_continue(url, limit):
            yield clip

    async def create_entitlement_grants_upload_url(self, params: _Params = None, *,
                                                   manifest_id: _Int = None,
                                                   type: str = None):
        url = 'https://api.twitch.tv/helix/entitlements/upload?'
        if params is None:
            params = {'manifest_id': manifest_id, 'type': type}

        if params.get('manifest_id') is None:
            raise TypeError('`manifest_id` must be not None')
        if params.get('type') is None:
            raise TypeError('`type` must be not None')

        url = insert_params(url, 0, params)
        response = await self._http_post(url, {})
        return response['data']

    async def get_code_status(self, limit: int, params: _Params = None, *,
                              code: _StrIter = None,
                              user_id: _Int = None):
        url = 'https://api.twitch.tv/helix/clips?'
        if params is None:
            params = {'code': code, 'user_id': user_id}

        if params.get('code') is None:
            TypeError('`code` must be not None')
        if params.get('user_id') is None:
            TypeError('`user_id` must be not None')

        url = insert_params(url, 0, params)
        async for code_status in self.to_be_continue(url, limit):
            yield code_status

    async def get_drops_entitlements(self, limit: int, params: _Params = None, *,
                                     entitlement_id: str = None,
                                     user_id: _Int = None,
                                     game_id: _Int = None):
        url = 'https://api.twitch.tv/helix/entitlements/drops?'
        if params is None:
            params = {}
            if entitlement_id: params['id'] = entitlement_id
            if user_id: params['user_id'] = user_id
            if game_id: params['game_id'] = game_id

        if params.get('entitlement_id') is not None:
            params['id'] = params.pop('entitlement_id', None)

        url = insert_params(url, limit, params)
        async for code_status in self.to_be_continue(url, limit):
            yield code_status

    async def redeem_code(self, params: _Params = None, *,
                          code: _StrIter = None,
                          user_id: _Int = None):
        url = 'https://api.twitch.tv/helix/entitlements/code?'
        if params is None:
            params = {'code': code, 'user_id': user_id}

        if params.get('code') is None:
            raise TypeError('`code` must be not None')
        if params.get('user_id') is None:
            raise TypeError('`user_id` must be not None')

        url = insert_params(url, 0, params)
        response = await self._http_post(url, {})
        return response['data']

    async def get_top_games(self, limit: int):
        url = 'https://api.twitch.tv/helix/games/top?'
        url = insert_params(url, limit, {})
        async for game in self.to_be_continue(url, limit):
            yield game

    async def get_games(self, limit: int, params: _Params = None, *,
                        game_id: _IntIter = None,
                        name: _StrIter = None):
        url = 'https://api.twitch.tv/helix/games?'
        if params is None:
            if game_id is not None:
                params['game_id'] = game_id
            if name is not None:
                params['name'] = name

        if params.get('game_id') is None and params.get('name') is None:
            raise TypeError('One or more of following args must be not None: `game_id`, `name`')

        url = insert_params(url, limit, {})
        async for game in self.to_be_continue(url, limit):
            yield game

    async def get_hype_train_events(self, limit: int, params: _Params = None, *,
                                    broadcaster_id: _IntIter = None,
                                    event_id: _StrIter = None):
        url = 'https://api.twitch.tv/helix/hypetrain/events?'
        if params is None:
            if broadcaster_id is not None:
                params['broadcaster_id'] = broadcaster_id
            if event_id is not None:
                params['id'] = event_id
        else:
            event_id = params.pop('event_id', None)
            if event_id is not None:
                params['id'] = event_id

        if params.get('broadcaster_id') is None:
            raise TypeError('`broadcaster_id` must be not None')

        url = insert_params(url, limit, {})
        async for game in self.to_be_continue(url, limit):
            yield game

    async def check_automod_status(self, data: _Data = None, *,
                                   broadcaster_id: _Int = None,
                                   msg_id: _StrIter = None,
                                   msg_text: _StrIter = None,
                                   user_id: _IntIter = None):
        url = 'https://api.twitch.tv/helix/moderation/enforcements/status?'

        if broadcaster_id is None:
            broadcaster_id = data.pop('broadcaster_id')
            if broadcaster_id is None:
                raise TypeError('`broadcaster_id` must be not None')

        if data is None:  # if `data` wasn't gave - create `data` by args
            data = await self.create_data_list(msg_id, msg_text, user_id)
        elif type(data) is list:  # if `data` is list - nothing have to do
            pass
        else:  # else args must be in `data` - checking, if one or more is None - `TypeError`
            if data.get('msg_id') is None:
                raise TypeError('`msg_id` must be not None')
            if data.get('msg_text') is None:
                raise TypeError('`msg_text` must be not None')
            if data.get('user_id') is None:
                raise TypeError('`user_id` must be not None')
            # if all is not None - create list
            data = await self.create_data_list(data['msg_id'], data['msg_text'], data['user_id'])

        url = insert_params(url, 0, {'broadcaster_id': broadcaster_id})
        response = await self._http_post(url, )
        return response['data']

    async def get_streams(self, limit: int, params: _Params = None, *,
                          game_id: _IntIter = None,
                          language: _StrIter = None,
                          user_id: _IntIter = None,
                          user_login: _IntIter = None):
        url = 'https://api.twitch.tv/helix/streams?'
        if params is None:
            params = {}
            if game_id: params['game_id'] = game_id
            if language: params['language'] = language
            if user_id: params['user_id'] = user_id
            if user_login: params['user_login'] = user_login

        url = insert_params(url, limit, params)
        async for stream in self.to_be_continue(url, limit):
            yield stream

    async def to_be_continue(self, url: str, limit: int):
        cursor = ''  # cursor, will be added in url
        counter = 0  # counter of iterations
        while True:  # loop will be breaks in conditions
            response = await self._http_get(url + cursor)  # getting data # first cursor is null
            for part in response['data']:
                yield part  # yield every part of data
                counter += 1  # incrementing the counter
                if counter == limit:  # if limit has been reached
                    return  # stop iteration

            pagination = response.get('pagination')  # getting container of cursor
            if pagination is not None:  # if this exists - cursor exists, so has more data
                cursor = '&after=' + pagination['cursor']  # save the cursor
            else:  # else - no more data
                return  # stop async iteration

    @staticmethod
    async def create_data_list(msg_id: _StrIter, msg_text: _StrIter, user_id: _IntIter) -> List[Dict]:
        # if one or more of that args is not `str` or `int` - chack that all of them is Iterable
        if not (type(msg_id) is str and type(msg_text) is str and (type(user_id) is int or type(user_id) is str)):
            if not (hasattr(msg_id, '__iter__')
                    and hasattr(msg_text, '__iter__')
                    and hasattr(user_id, '__iter__')
                    and type(user_id) is not str):  # if not all is `Iterable` - `TypeError`
                raise TypeError('`msg_id`, `msg_text`, `user_id` must be all Iterable or all not Iterable')
            # if all is Iterable - check that `len`s equal, if not - `WrongIterObjects`
            if not (len(msg_id) == len(msg_text) == len(user_id)):
                raise WrongIterObjects('`lens` of `msg_id`, `msg_text`, `user_id` must equal')
            data = []  # data to return
            for i in range(len(msg_id)):  # loop to create dicts
                current_dict = {'msg_id': msg_id[i],
                                'msg_text': msg_text[i],
                                'user_id': user_id[i]}
                data.append(current_dict)  # all dicts must be in `list`
            return data
        # if all is `str` or `int`
        current_dict = {'msg_id': msg_id,
                        'msg_text': msg_text,
                        'user_id': user_id}
        data = [current_dict]
        return data

    # we need many of http requests, so for clear code - putted it in functions
    async def _http_get(self, url: str):
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPError(await response.json())
                return await response.json()

    async def _http_post(self, url: str, data: Dict):
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    raise HTTPError(await response.json())
                return await response.json()

    async def _http_put(self, url: str, data: Dict):
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.put(url, data=data) as response:
                if response.status != 200:
                    raise HTTPError(await response.json())
                return await response.json()

    async def _http_patch(self, url: str, data: Dict):
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.patch(url, data=data) as response:
                if response.status != 200:
                    raise HTTPError(await response.json())
                return await response.json()

    async def _http_delete(self, url: str):
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.patch(url) as response:
                if response.status != 204:  # here is 204(No data) instead of 200, cuz `delete` returns nothing
                    raise HTTPError(await response.json())
                return None  # so we return None
