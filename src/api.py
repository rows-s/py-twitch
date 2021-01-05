

import aiohttp

from errors import HTTPError, InvalidToken, WrongIterObjects, ServerError, AccessError

from typing import Dict, Union, Iterable, List

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
        self._session = aiohttp.ClientSession()

    async def set_auth(self, auth: str):
        headers = {'Authorization': 'Bearer ' + auth}
        url = 'https://id.twitch.tv/oauth2/validate'  # url to check auth
        async with self._session.get(url, headers=headers) as response:
            json = await response.json()
            if response.status == 401:  # 401 - invalid token
                raise InvalidToken(json)
            if response.status == 500:  # 500 - server's problems
                raise ServerError(json)
            headers['Client-Id'] = json['client_id']
            self._headers = headers
            self._scopes = json['scopes']
            await self._session.close()
            self._session = aiohttp.ClientSession(headers=self._headers)

    async def start_commercial(self,
                               broadcaster_id: _Int = None,
                               length: _Int = None):
        scope = 'channel:edit:commercial'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token has\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')
        if length is None:
            raise TypeError('`length` must be not None')

        data = {'broadcaster_id': broadcaster_id, 'length': length}
        params = {}

        url = 'https://api.twitch.tv/helix/channels/commercial'
        response = await self._http_post(url, data, params)
        return response['data'][0]

    async def get_extension_analytics(self, limit: int,
                                      extension_id: str = None,
                                      started_at: str = None,
                                      ended_at: str = None,
                                      type: str = None):
        scope = 'analytics:read:extensions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token has\'t required scope: `{scope}`')

        params = {'extension_id': extension_id, 'started_at': started_at, 'ended_at': ended_at, 'type': type}
        self._delete_none(params)  # delete all `None` params
        if limit > 0:  # if (limit <= 0)(unlimited) - we will receive responses with default `first`(20)
            first = min(100, limit)  # `first` can't be more than 100, if more - set 100
            params['first'] = first  # set `first` param

        url = 'https://api.twitch.tv/helix/analytics/extensions'
        async for extension in self.to_be_continue(url, limit, params):
            yield extension

    async def get_game_analytics(self, limit: int,
                                 game_id: _Int = None,
                                 started_at: str = None,
                                 ended_at: str = None,
                                 type: str = None):
        scope = 'analytics:read:games'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token has\'t required scope: `{scope}`')

        params = {'game_id': game_id, 'started_at': started_at, 'ended_at': ended_at, 'type': type}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/analytics/games'
        async for game in self.to_be_continue(url, limit, params):
            yield game

    async def get_bits_leaderboard(self, limit: int,
                                   period: str = None,
                                   started_at: str = None,
                                   user_id: _Int = None):
        scope = 'bits:read'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token has\'t required scope: `{scope}`')

        params = {'period': period, 'started_at': started_at, 'user_id': user_id}
        self._delete_none(params)
        if limit > 0:
            count = min(100, limit)
            params['count'] = count  # this request takes `count` instead of `first`
        else:
            params['count'] = 100  # and this request has global limit of results - 100

        url = 'https://api.twitch.tv/helix/bits/leaderboard'
        async for leader in self.to_be_continue(url, limit, params):
            yield leader

    async def get_cheermotes(self, limit: int, broadcaster_id: _Int = None):
        params = {'broadcaster_id': broadcaster_id}
        self._delete_none(params)

        url = 'https://api.twitch.tv/helix/bits/cheermotes'
        async for cheermote in self.to_be_continue(url, limit, params):
            yield cheermote

    async def get_extension_transactions(self, limit: int,
                                         extension_id: str = None,
                                         transaction_id: _StrIter = None):
        if extension_id is None:
            raise TypeError('`extension_id` must be not None')

        params = {'extension_id': extension_id, 'id': transaction_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/extensions/transactions'
        async for transaction in self.to_be_continue(url, limit, params):
            yield transaction

    async def create_custom_rewards(self,
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
        scope = 'channel:manage:redemptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if title is None:
            raise TypeError('`title`must be not None')
        if cost is None:
            raise TypeError('`cost` must be not None')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        data = {'cost': cost,
                'title': title,
                'prompt': prompt,
                'is_enabled': is_enabled,
                'max_per_stream': max_per_stream,
                'background_color': background_color,
                'is_user_input_required': is_user_input_required,
                'max_per_user_per_stream': max_per_user_per_stream,
                'global_cooldown_seconds': global_cooldown_seconds,
                'is_max_per_stream_enabled': is_max_per_stream_enabled,
                'is_global_cooldown_enabled': is_global_cooldown_enabled,
                'is_max_per_user_per_stream_enabled': is_max_per_user_per_stream_enabled,
                'should_redemptions_skip_request_queue': should_redemptions_skip_request_queue}
        self._delete_none(data)
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
        response = await self._http_post(url, data, params)
        return response['data'][0]

    async def delete_custom_reward(self,
                                   broadcaster_id: _Int = None,
                                   reward_id: str = None):
        scope = 'channel:manage:redemptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')
        if reward_id is None:
            raise TypeError('`reward_id`(`id`) must be not None')

        params = {'broadcaster_id': broadcaster_id, 'id': reward_id}

        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
        await self._http_delete(url, params)
        return None

    async def get_custom_reward(self, limit: int,
                                broadcaster_id: _Int = None,
                                reward_id: _StrIter = None,
                                only_manageable_rewards: _Bool = None):
        scope = 'channel:manage:redemptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'id': reward_id, 'only_manageable_rewards': only_manageable_rewards}
        self._delete_none(params)

        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
        async for reward in self.to_be_continue(url, limit, params):
            yield reward

    async def get_custom_reward_redemption(self, limit: int,
                                           broadcaster_id: _Int = None,
                                           reward_id: str = None,
                                           id: _StrIter = None,
                                           status: str = None,
                                           sort: str = None):
        scope = 'channel:manage:redemptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')
        if reward_id is None:
            raise TypeError('`reward_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'reward_id': reward_id, 'id': id, 'status': status, 'sort': sort}
        self._delete_none(params)
        if limit > 0:
            first = min(50, limit)  # `first` has limit of 50 for this request
            params['first'] = first

        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions'
        async for reward in self.to_be_continue(url, limit, params):
            yield reward

    async def update_custom_reward(self,
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
        scope = 'channel:manage:redemptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')
        if reward_id is None:
            raise TypeError('`reward_id` must be not None')

        data = {'cost': cost,
                'title': title,
                'prompt': prompt,
                'is_paused': is_paused,
                'is_enabled': is_enabled,
                'max_per_stream': max_per_stream,
                'background_color': background_color,
                'is_user_input_required': is_user_input_required,
                'max_per_user_per_stream': max_per_user_per_stream,
                'global_cooldown_seconds': global_cooldown_seconds,
                'is_max_per_stream_enabled': is_max_per_stream_enabled,
                'is_global_cooldown_enabled': is_global_cooldown_enabled,
                'is_max_per_user_per_stream_enabled': is_max_per_user_per_stream_enabled,
                'should_redemptions_skip_request_queue': should_redemptions_skip_request_queue}
        self._delete_none(data)
        params = {'broadcaster_id': broadcaster_id, 'id': reward_id}

        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
        response = await self._http_patch(url, data, params)
        return response['data'][0]

    async def update_redemption_status(self,
                                       broadcaster_id: _Int = None,
                                       reward_id: str = None,
                                       id: _StrIter = None,
                                       status: str = None):
        scope = 'channel:manage:redemptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')
        if reward_id is None:
            raise TypeError('`reward_id` must be not None')
        if id is None:
            raise TypeError('`id` must be not None')
        if status is None:
            raise TypeError('`status` must be secified')

        data = {'status': status}
        params = {'broadcaster_id': broadcaster_id, 'reward_id': reward_id, 'id': id}

        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions'
        response = await self._http_patch(url, data, params)
        return response['data'][0]

    async def create_clip(self,
                          broadcaster_id: _Int = None,
                          has_delay: _Bool = None):
        scope = 'clips:edit'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        data = {}
        params = {'broadcaster_id': broadcaster_id, 'has_delay': has_delay}
        self._delete_none(params)

        url = 'https://api.twitch.tv/helix/clips'
        response = await self._http_post(url, data, params)
        return response['data']

    async def get_clips(self, limit: int,
                        broadcaster_id: _Int = None,
                        game_id: _Int = None,
                        clip_id: _StrIter = None,
                        started_at: str = None,
                        ended_at: str = None):
        if broadcaster_id is None \
                and game_id is None \
                and clip_id is None:  # if all 3 is None - TypeError, one or more must be specified
            raise TypeError('One of following args must be not None: `broadcaster_id` or `game_id` or `clip_id`')

        params = {'broadcaster_id': broadcaster_id, 'game_id': game_id, 'clip_id': clip_id,
                  'started_at': started_at, 'ended_at': ended_at}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/clips'
        async for clip in self.to_be_continue(url, limit, params):
            yield clip

    async def create_entitlement_grants_upload_url(self,
                                                   manifest_id: _Int = None,
                                                   type: str = None):
        if manifest_id is None:
            raise TypeError('`manifest_id` must be not None')
        if type is None:
            raise TypeError('`type` must be not None')

        data = {}
        params = {'manifest_id': manifest_id, 'type': type}

        url = 'https://api.twitch.tv/helix/entitlements/upload'
        response = await self._http_post(url, data, params)
        return response['data']

    async def get_code_status(self, limit: int,
                              code: _StrIter = None,
                              user_id: _Int = None):
        if code is None:
            TypeError('`code` must be not None')
        if user_id is None:
            TypeError('`user_id` must be not None')

        params = {'code': code, 'user_id': user_id}

        url = 'https://api.twitch.tv/helix/entitlements/codes'
        async for code_status in self.to_be_continue(url, limit, params):
            yield code_status

    async def get_drops_entitlements(self, limit: int,
                                     entitlement_id: str = None,
                                     user_id: _Int = None,
                                     game_id: _Int = None):
        params = {'id': entitlement_id, 'user_id': user_id, 'game_id': game_id}
        self._delete_none(params)

        url = 'https://api.twitch.tv/helix/entitlements/drops'
        async for code_status in self.to_be_continue(url, limit, params):
            yield code_status

    async def redeem_code(self,
                          code: _StrIter = None,
                          user_id: _Int = None):
        if code is None:
            raise TypeError('`code` must be not None')
        if user_id is None:
            raise TypeError('`user_id` must be not None')

        data = {}
        params = {'code': code, 'user_id': user_id}

        url = 'https://api.twitch.tv/helix/entitlements/code'
        response = await self._http_post(url, data, params)
        return response['data']

    async def get_top_games(self, limit: int):
        params = {}
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/games/top'
        async for game in self.to_be_continue(url, limit, params):
            yield game

    async def get_games(self, limit: int,
                        game_id: _IntIter = None,
                        name: _StrIter = None):
        if game_id is None and name is None:
            raise TypeError('One or more of following args must be specified: `game_id`, `name`')

        params = {'game_id': game_id, 'name': name}
        self._delete_none(params)

        url = 'https://api.twitch.tv/helix/games'
        async for game in self.to_be_continue(url, limit, params):
            yield game

    async def get_hype_train_events(self, limit: int,
                                    broadcaster_id: _Int = None,
                                    event_id: _StrIter = None):
        scope = 'channel:read:hype_train'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'id': event_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first  # Default `first` - 1

        url = 'https://api.twitch.tv/helix/hypetrain/events'
        async for event in self.to_be_continue(url, limit, params):
            yield event

    async def check_automod_status(self,
                                   broadcaster_id: _Int = None,
                                   msg_id: _StrIter = None,
                                   msg_text: _StrIter = None,
                                   user_id: _IntIter = None):
        scope = 'moderation:read'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')

        data = {}
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/moderation/enforcements/status'
        response = await self._http_post(url, data, params)
        return response['data']

    async def get_banned_events(self, limit: int,
                                broadcaster_id: _Int = None,
                                user_id: _IntIter = None):
        scope = 'moderation:read'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'user_id': user_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/moderation/banned/events'
        async for event in self.to_be_continue(url, limit, params):
            yield event

    async def get_banned_users(self, limit: int,
                               broadcaster_id: _Int = None,
                               user_id: _IntIter = None):
        scope = 'moderation:read'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'user_id': user_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/moderation/banned'
        async for user in self.to_be_continue(url, limit, params):
            yield user

    async def get_moderators(self, limit: int,
                             broadcaster_id: _Int = None,
                             user_id: _IntIter = None):
        scope = 'moderation:read'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'user_id': user_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/moderation/moderators'
        async for moderator in self.to_be_continue(url, limit, params):
            yield moderator

    async def get_moderator_events(self, limit: int,
                                   broadcaster_id: _Int = None,
                                   user_id: _IntIter = None):
        scope = 'moderation:read'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be not None')

        params = {'broadcaster_id': broadcaster_id, 'user_id': user_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/moderation/moderators/events'
        async for event in self.to_be_continue(url, limit, params):
            yield event

    async def search_categories(self, limit: int, query: str):
        params = {'query': query}
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/search/categories'
        async for category in self.to_be_continue(url, limit, params):
            yield category

    async def search_channels(self, limit: int, query: str):
        params = {'query': query}
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/search/channels'
        async for channel in self.to_be_continue(url, limit, params):
            yield channel

    async def get_stream_key(self, broadcaster_id: int):
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/streams/key'
        stream_key = await self._http_get(url, params)
        return stream_key['data'][0]['stream_key']

    async def get_streams(self, limit: int,
                          game_id: _IntIter = None,
                          language: _StrIter = None,
                          user_id: _IntIter = None,
                          user_login: _StrIter = None):
        params = {'game_id': game_id, 'language': language, 'user_id': user_id, 'user_login': user_login}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/streams'
        async for stream in self.to_be_continue(url, limit, params):
            yield stream

    async def create_stream_marker(self,
                                   user_id: _Int = None,
                                   description: str = None):
        scope = 'user:edit:broadcast'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if user_id is None:
            raise TypeError('`user_id` must be not None')

        data = {'user_id': user_id, 'description': description}
        self._delete_none(data)
        params = {}

        url = 'https://api.twitch.tv/helix/streams/markers'
        response = await self._http_post(url, data, params)
        return response['data'][0]

    async def get_stream_markers(self, limit: int,
                                 user_id: _IntIter = None,
                                 video_id: _StrIter = None):
        scope = 'user:read:broadcast'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if user_id is None and video_id is None:
            raise TypeError('One or more of following params must be specified: `user_id`, `video_id`')

        params = {'user_id': user_id, 'video_id': video_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/streams/markers'
        async for marker in self.to_be_continue(url, limit, params):
            yield marker

    async def get_channel_information(self, broadcaster_id: int):
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/channels'
        info = await self._http_get(url, params)
        return info['data'][0]

    async def modify_channel_information(self,
                                         broadcaster_id: _Int = None,
                                         game_id: _Int = None,
                                         broadcaster_language: str = None,
                                         title: str = None):
        scope = 'user:edit:broadcast'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be specified')
        if game_id is None and broadcaster_language is None and title is None:
            TypeError('One or more of following params must be specified: `game_id`, `broadcaster_language`, `title`')

        data = {'game_id': game_id, 'broadcaster_language': broadcaster_language, 'title': title}
        self._delete_none(data)
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/channels'
        await self._http_patch(url, data, params)
        return None

    async def get_broadcaster_subscriptions(self, limit: int,
                                            broadcaster_id: _Int = None,
                                            user_id: _StrIter = None):
        scope = 'channel:read:subscriptions'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be specified')

        params = {'broadcaster_id': broadcaster_id, 'user_id': user_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/subscriptions'
        async for subscription in self.to_be_continue(url, limit, params):
            yield subscription

    async def get_all_stream_tags(self, limit: int, tag_id: _StrIter = None):
        params = {'tag_id': tag_id}
        self._delete_none(params)
        if limit > 0:
            first = min(100, limit)
            params['first'] = first

        url = 'https://api.twitch.tv/helix/tags/streams'
        async for tag in self.to_be_continue(url, limit, params):
            yield tag

    async def get_stream_tags(self, limit: int, broadcaster_id: _Int):
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/streams/tags'
        async for tag in self.to_be_continue(url, limit, params):
            yield tag

    async def replace_stream_tags(self,
                                  broadcaster_id: _Int = None,
                                  tag_ids: _StrIter = None):
        scope = 'user:edit:broadcast'
        if scope not in self._scopes:
            raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')
        if broadcaster_id is None:
            raise TypeError('`broadcaster_id` must be specified')

        if type(tag_ids) is str:  # `tag_ids` must be list - so, if `str` - put in list
            data = {'tag_ids': [tag_ids]}
        else:  # else, must be Iterable, convert to list
            data = {'tag_ids': list(tag_ids)}
        params = {'broadcaster_id': broadcaster_id}

        url = 'https://api.twitch.tv/helix/streams/tags'
        await self._http_put(url, {}, params, json=data)
        return None

    async def to_be_continue(self, url: str, limit: int, params: dict):
        counter = 0  # counter of iterations
        while True:  # loop will be breaks in conditions
            response = await self._http_get(url, params)  # getting data # at first `after`(cursor) is None
            for part in response['data']:
                yield part  # yield every part of data
                counter += 1  # increasing the counter value
                if counter == limit:  # if limit is reached - stop async iteration
                    return
            pagination = response.get('pagination')  # getting container of cursor
            if pagination is not None:  # if the container exists - cursor exists, so set it
                params['after'] = pagination['cursor']  # add `after`(cursor) paramor change it
            else:  # else - no more data - stop async iteration
                return

    @staticmethod
    def create_data_list(msg_id: _StrIter, msg_text: _StrIter, user_id: _IntIter) -> List[Dict]:
        # if one or more of that args is not `str` or `int` - check that all of them is Iterable
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

    @staticmethod
    def _delete_none(params: dict):
        keys = list(params.keys())
        for key in keys:
            if params[key] is None:
                params.pop(key)

    # we need many of http requests, so for clear code - put them in functions
    async def _http_get(self, url: str, params: dict):
        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                raise HTTPError(await response.json())
            return await response.json()

    async def _http_post(self, url: str, data: dict, params: dict):
        async with self._session.post(url, data=data, params=params) as response:
            if response.status != 200:
                raise HTTPError(await response.json())
            return await response.json()

    async def _http_put(self, url: str, data: dict, params: dict, *, json: dict = None):
        if json is not None:
            async with self._session.put(url, json=json, params=params) as response:
                if response.status != 200:
                    if response.status == 204:
                        return None
                    raise HTTPError(await response.json())
                return await response.json()
        async with self._session.put(url, data=data, params=params) as response:
            if response.status != 200:
                if response.status == 204:
                    return None
                raise HTTPError(await response.json())
            return await response.json()

    async def _http_patch(self, url: str, data: dict, params: dict):
        async with self._session.patch(url, data=data, params=params) as response:
            if response.status != 200:
                if response.status == 204:
                    return None
                raise HTTPError(await response.json())
            return await response.json()

    async def _http_delete(self, url: str, params: dict):
        async with self._session.patch(url, params=params) as response:
            if response.status != 204:  # here is 204(No data) instead of 200, cuz `delete` returns nothing
                raise HTTPError(await response.json())
            return None  # so we return None

    async def close(self):
        await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.close()
