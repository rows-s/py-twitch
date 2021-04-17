import aiohttp
from aiohttp.client import ClientResponse
from aiohttp.client_exceptions import ContentTypeError
from dataclasses import dataclass, InitVar

from errors import HTTPError, InvalidToken, AccessError

from typing import Dict, Union, Iterable, List, Optional, AsyncGenerator, Any, Callable, Tuple, Awaitable

__all__ = (
    'Api',
)


@dataclass()
class BaseRequest:
    sub_url: InitVar[str]
    data_params_keys: Iterable[str] = ()
    query_params_keys: Iterable[str] = ()
    scope: Optional[str] = None

    def __post_init__(self, sub_url: str):
        helix_url: str = 'https://api.twitch.tv/helix'
        self.url: str = helix_url + sub_url

    @staticmethod
    def not_none_fromkeys(
            raw_dict: dict,
            keys_to_select: Iterable[Any]
    ):
        final_dict: Dict[str, Any] = {}
        for key in keys_to_select:
            if raw_dict.get(key) is not None:
                final_dict[key] = raw_dict[key]
        return final_dict

    def distribute_raw_params(
            self,
            raw_params: Dict[str, Any],
            *args,
            **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        raw_params = raw_params.copy()
        raw_params.update(kwargs)
        data_params = self.not_none_fromkeys(raw_params, self.data_params_keys)
        query_params = self.not_none_fromkeys(raw_params, self.query_params_keys)
        return data_params, query_params


@dataclass()
class SingleRequest(BaseRequest):
    http_method: Callable = None
    response_json_preparer: Callable[[dict], Any] = lambda json: json['data'][0] if (json is not None) else json

    def __post_init__(self, sub_url: str):
        super().__post_init__(sub_url)
        if self.http_method is None:
            raise NotImplementedError('http_method must be specified')


@dataclass()
class PaginatedRequest(BaseRequest):
    max_first: int = 100
    response_json_preparer: Callable[[dict], Iterable] = lambda json: json['data'] if (json is not None) else ()

    def calc_first_param(
            self,
            limit: int
    ) -> Optional[int]:
        if limit > 0:
            first: int = min(limit, self.max_first)
            return first
        else:
            return None

    def distribute_raw_params(
            self,
            raw_params: Dict[str, Any],
            limit: int,
            *args,
            **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if 'first' in self.query_params_keys:
            first = self.calc_first_param(limit=limit)
            if first is not None:
                kwargs['first'] = first
        return super(PaginatedRequest, self).distribute_raw_params(raw_params, *args, **kwargs)


class Api:
    """
        This class gives you ability to easy use twtich-API.

        Attrs:
            token: `Optional[str]`
                Authorization-Token, would be set in set_token() method
            client_id: `Optional[str]`
                client id of current token, would be set in set_token() method
            scopes: `List[str]`
                scopes of current token, would be set in set_token() method
            expires_in: `Optional[int]`
                count of seconds of rest of life of current token since set_token() called

        Notes:
            1st:
                Before calling a request, Authorization-Token must be set, see self.set_token() and Api.create() methods
            2nd:
                All object attributes is None before set_token() is successfully called
        """

    def __init__(self):
        self._headers: Optional[Dict[str, str]] = None
        self.token: Optional[str] = None
        self.scopes: Optional[List[str]] = None
        self.client_id: Optional[str] = None
        self.expires_in: Optional[int] = None

    #################################
    # initialization methods
    #
    @classmethod
    async def create(
            cls,
            token: str
    ):
        """
        |Coroutine|

        if you want to create and initialize object (set token) in one row, use this.
        The method creates object and calls `self.set_token()` method for the object with given `token`.

        Args:
            token: `str`
                your Authorization-token

        Examples:
            1. >>>> ttv_api = await Api.create(api_token)

        Returns:
            `Api` created and initialized object
        """

        api = Api()
        await api.set_token(token)
        return api

    async def set_token(
            self,
            token: str
    ) -> None:
        """
        |Coroutine|

        sets:
            1. `self.token`
            2. `self.client_id`
            3. `self.scopes`
            4. `self.expires_at`
            5. prepares header for requests

        Args:
            token: `str`
                your Authorization-Token

        Raises:
            HTTPError:
                if status-code of response is not 2XX or 4XX. passes response.
            InvalidToken:
                if `token` is invalid, passes `dict` with json of response. passes response.
        """

        self._headers = {'Authorization': f'Bearer {token}'}
        url = 'https://id.twitch.tv/oauth2/validate'  # url to check token
        try:
            json = await self._get_response(
                self._get_open_session().get(url, headers=self._headers)
            )
        except HTTPError as e:
            response: ClientResponse = e.args[0]
            if 399 < response.status < 500:  # 4XX - invalid token
                raise InvalidToken(response)
            else:
                raise
        else:
            self.token = token
            self.client_id = json['client_id']
            self._headers['Client-Id'] = json['client_id']
            self.expires_in = json['expires_in']
            self.scopes = json['scopes']

    @classmethod
    async def create_app_token(
            cls,
            client_id: str,
            client_secret: str,
            scope: str = None,
            grant_type: str = 'client_credentials'
    ) -> Dict[str, str]:
        """
        |Coroutine|

        creates an app `token`

        Args:
        ----------
            client_id: `str`
                Your client ID
            client_secret: `str`
                Your client secret
            grant_type: `str`
                1. VALID VALUES: 'client_credentials'; DEFAULT'client_credentials';
                2. not described
            scope: `str`
                Space-separated list of scopes

        Returns:
        ----------
            dict: {
                'access_token': `str`
                    user access token
                'refresh_token': `str`
                    not described
                'expires_in': `str`
                    number of seconds until the token expires
                'scope': `str`
                    your previously listed scope(s)
                'token_type': `str`
                    bearer
            }

        Raises:
            HTTPError:
                if status-code of response is not 2XX. passes response.
        """

        params = {}
        if client_id is not None:
            params['client_id'] = client_id
        if client_secret is not None:
            params['client_secret'] = client_secret
        if scope is not None:
            params['scope'] = scope
        if grant_type is not None:
            params['grant_type'] = grant_type

        url = 'https://id.twitch.tv/oauth2/token'  # url to create app token
        json = await cls._get_response(
            cls._get_open_session().post(url, params=params)
        )
        return json
    #
    # initialization methods
    #################################

    #################################
    # requests methods
    #
    _session: aiohttp.ClientSession = None
    'session container'

    @staticmethod
    def _get_open_session():
        """
        returns open session, if `Api._session` is open -> `Api._session`.
        else -> open new one, save to `Api._session` and return

        Returns:
            (aiohttp.ClientSession)
        """
        if Api._session is None:
            Api._session = aiohttp.ClientSession()
        elif Api._session.closed:
            Api._session = aiohttp.ClientSession()
        # return anyway
        return Api._session

    @classmethod
    async def close(cls):
        await cls._session.close()

    @staticmethod
    async def _get_response(
            request: Awaitable
    ) -> Optional[Dict]:
        async with request as response:
            if 199 < response.status < 300:
                try:
                    return await response.json()
                except ContentTypeError:
                    return None
            else:
                raise HTTPError(response)

    async def _http_get(
            self,
            url: str,
            data: dict = None,
            params: dict = None
    ) -> Optional[dict]:
        json = await self._get_response(
            self._get_open_session().get(url, data=data, params=params, headers=self._headers)
        )
        return json

    async def _http_post(
            self,
            url: str,
            data: dict = None,
            params: dict = None
    ) -> Optional[dict]:
        json = await self._get_response(
            self._get_open_session().post(url, json=data, params=params, headers=self._headers)
        )
        return json

    async def _http_put(
            self,
            url: str,
            data: dict = None,
            params: dict = None
    ) -> Optional[dict]:
        json = await self._get_response(
            self._get_open_session().put(url, json=data, params=params, headers=self._headers)
        )
        return json

    async def _http_patch(
            self,
            url: str,
            data: dict = None,
            params: dict = None
    ) -> Optional[dict]:
        json = await self._get_response(
            self._get_open_session().patch(url, json=data, params=params, headers=self._headers)
        )
        return json

    async def _http_delete(
            self,
            url: str,
            data: dict = None,
            params: dict = None
    ) -> Optional[dict]:
        json = await self._get_response(
            self._get_open_session().delete(url, data=data, params=params, headers=self._headers)
        )
        return json

    def _check_scope(
            self,
            scope: str
    ) -> None:
        """
        Raises `AccessError` if current token hasn't required scope

        Args:
            scope: `str`
                scope to check

        Returns:
            `None`

        Raises:
            `AccessError`: if the object hasn't required scope
        """
        if scope is not None:
            if scope not in self.scopes:
                raise AccessError(f'Current auth-token hasn\'t required scope: `{scope}`')

    @staticmethod
    def _set_additional_data(
            all_data: dict,
            additional_data: dict
    ) -> None:
        """sets all items from `all_data` into `additional_data` except root item with 'data' as key"""
        if all_data is not None:
            for key in all_data:
                if key != 'data':
                    additional_data[key] = all_data[key]

    async def do_single_request_by_name(
            self,
            request_name: str,
            raw_params: dict,
            *,
            additional_data: Optional[dict] = None
    ):
        """returns object that got from called method `self.do_single_request`"""
        request = Api.single_requests[request_name]
        return await self.do_single_request(request, raw_params, additional_data=additional_data)

    async def do_paginated_request_by_name(
            self,
            request_name: str,
            raw_params: dict,
            limit: int,
            *,
            additional_data: Optional[dict] = None
    ):

        """yields all that yields called method `self.do_paginated_request`"""
        request = Api.paginated_requests[request_name]
        async for json_part in self.do_paginated_request(request, raw_params, limit, additional_data=additional_data):
            yield json_part

    async def do_single_request(
            self,
            request: SingleRequest,
            raw_params: Dict[str, Any],
            *,
            additional_data: Optional[dict] = None
    ) -> Any:
        """Does single request based on url from `request.url`, with selected not None params from `raw_params`
        basing on `request.data_params_keys` and `request.query_params_keys`"""
        # prepare data
        self._check_scope(request.scope)
        data, params = request.distribute_raw_params(raw_params)
        # get request
        json = await request.http_method(self, url=request.url, data=data, params=params)
        if additional_data is not None:
            self._set_additional_data(json, additional_data)
        return request.response_json_preparer(json)

    async def do_paginated_request(
            self,
            request: PaginatedRequest,
            raw_params: Dict[str, Any],
            limit: int,
            *,
            additional_data: Optional[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """Does single request based on url from `request.url`, with selected not None params from `raw_params`
        basing on `request.data_params_keys` and `request.query_params_keys`"""
        self._check_scope(request.scope)
        data, params = request.distribute_raw_params(raw_params, limit)
        async for json_part in self._handle_pagination(request.url, limit, data, params,
                                                       response_json_preparer=request.response_json_preparer,
                                                       additional_data=additional_data):
            yield json_part

    async def _handle_pagination(
            self,
            url: str,
            limit: int,
            data: Optional[dict] = None,
            params: Optional[dict] = None,
            *,
            response_json_preparer: Callable[[dict], Iterable] = lambda json: json['data'] if (json is not None) else [],
            additional_data: Optional[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|

        Method implements simple request, limit and cursor handler
        Handles cursor if exists and limits count of yields

        Args:
            data (Union[dict]):
                data to send as JSON
            url: `str`
                URL for request
            limit: `int`
                value of max count of Yields
            params: `dict`
                params to insert in the URL

        Yields:
            splitted data of the response of the request
        """
        counter = 0
        while True:
            json = await self._http_get(url=url, data=data, params=params)
            if additional_data is not None:
                self._set_additional_data(json, additional_data)
            # parse
            for part in response_json_preparer(json):
                yield part
                # if limit is reached
                counter += 1
                if counter == limit:  # if limit is 0 -> never True (unlimited)
                    return
            # prepare to new
            else:
                try:
                    cursor = json['pagination']['cursor']
                # if can't get
                except KeyError:
                    return
                # if have got
                else:
                    params['after'] = cursor  # set or change

    @staticmethod
    async def once(
            generator: AsyncGenerator[Any, Any]
    ) -> Optional[dict]:
        """
        The method gives you simple way to get only one result from any async generator in one code-row.\n
        Gets initialized async generator (object of async generator).

        ----------------

        Examples::
        ===================
            1st:
                api = Api.create(token) \n
                top_stream = await api.once(api.get_streams(limit=1))

            2nd:
                api = Api.create(token) \n
                generator_obj = api.get_streams(limit=1) \n
                top_stream = await api.once(generator_obj)

            both of examples do the same thing, \n
            2nd is here for more visual that the `generator` as argument is 'object of async generator',
            not 'async generator'
        ----------------

        Args:
        =================
            generator:
                Object of async generator
        ----------------

        Returns:
        ==================
            Dict:
                if get result from the `generator`

            None:
                if the `generator` returned nothing(if raised StopAsyncIteration)
        ----------------
        """
        try:
            return await generator.__anext__()
        except StopAsyncIteration:
            return None
    #
    # requests methods
    #################################

    async def start_commercial(
            self,
            broadcaster_id: str,
            length: int
    ) -> Dict[str, str]:
        """
        |Coroutine|

        Starts a commercial on a specified channel.

        1. SCOPE: 'channel:edit:commercial'
        2. ACCESS: OAuth Token required

        Args:
        ----------
            broadcaster_id: `str`
                1. REQUIRED;
                2. ID of the channel requesting a commercial. Minimum: 1 Maximum: 1
            length: `int`
                1. REQUIRED;  VALID VALUES: 30 60 90 120 150 180;
                2. Desired length of the commercial in seconds.

        Returns:
        ----------
            dict: {
                'length': `int`
                    Length of the triggered commercial
                'message': `str`
                    Provides contextual information on why the request failed
                'retry_after': `int`
                    Seconds until the next commercial can be served on this channel
            }

        Raises:
            HTTPError:
                if status-code of response is not 2XX. passes response.
            AccessError:
                if the Token has not required scope. passes response.

Input type:
        """
        return await self.do_single_request_by_name('start_commercial', locals())

    async def get_extension_analytics(
            self,
            limit: int,
            extension_id: str = None,
            started_at: str = None,
            ended_at: str = None,
            type: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Gets a URL that Extension developers can use to download analytics reports (CSV files) for their Extensions. The
        URL is valid for 5 minutes.If you specify a future date, the response will be “Report Not Found For Date Range.”
        If you leave both `started_at` and `ended_at` blank, the API returns the most recent date of data.

        1. SCOPE: 'analytics:read:extensions'
        2. ACCESS: OAuth token required

        Args:
        ----------
            limit: `int`
                1. REQUIRED;
                2. limit on number of yields, 0 - unlimited
            extension_id: `str`
                Client ID value assigned to the extension when it is created.  If this is specified, the returned URL
                points to an analytics report for just the specified extension. If this is not specified, the response
                includes multiple URLs, pointing to separate analytics reports for each of the authenticated user’s
                Extensions.
            ended_at: `str`
                1. DEFAULT: '1-2 days before the request was issued';
                2. Ending date/time for returned reports, in RFC3339 format with the hours, minutes, and seconds zeroed
                   out and the UTC timezone: 'YYYY-MM-DDT00:00:00Z'. The report covers the entire ending date; e.g., if
                   '2018-05-01T00:00:00Z' is specified, the report covers up to '2018-05-01T23:59:59Z'. If this is
                   provided, started_at also must be specified. If ended_at is later than the default end date, the
                   default date is used. Default: 1-2 days before the request was issued (depending on report
                   availability).
            started_at: `str`
                1. DEFAULT: 'This must be on or after January 31, 2018';
                2. Starting date/time for returned reports, in RFC3339 format with the hours, minutes, and seconds
                   zeroed out and the UTC timezone: 'YYYY-MM-DDT00:00:00Z'. This must be on or after January 31, 2018.If
                   this is provided, `ended_at` also must be specified. If `started_at` is earlier than the default
                   start date, the default date is used. The file contains one row of data per day.
            type: `str`
                1. DEFAULT: 'overview_v2';
                2. Type of analytics report that is returned. Currently, this field has no affect on the response as
                   there is only one report type. If additional types were added, using this field would return only the
                   URL for the specified report. Limit: 1. Valid values: 'overview_v2'.

        Yields:
        ----------
            dict: {
                'extension_id': `str`
                    ID of the extension whose analytics data is being provided.
                'URL': `str`
                    URL to the downloadable CSV file containing analytics data. Valid for 5 minutes.
                'type': `str`
                    Type of report.
                'date_range': {
                    'started_at': `str`
                        Report start date/time. Note this may differ from (be later than) the started_at value in the
                        request; the response value is the date when data for the extension is available.
                    'ended_at': `str`
                        Report end date/time.
                }, object contains data range parameters
            }

        Raises:
            HTTPError:
                if status-code of response is not 2XX. passes response.
            AccessError:
                if the Token has not required scope. passes response.
        """
        async for extension_analytic in self.do_paginated_request_by_name('get_extension_analytics', locals(), limit):
            yield extension_analytic

    async def get_game_analytics(
            self,
            limit: int,
            game_id: str = None,
            started_at: str = None,
            ended_at: str = None,
            type: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Yields URL that game developers can use to download analytics reports (CSV files) for their games.
        The URL is valid for 5 minutes.

        1. SCOPE: 'analytics:read:games'
        2. TOKEN: OAuth token required

        Args:
        ----------
            limit: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. limit on number of yields, 0 - unlimited
            game_id: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Game ID. If this is specified,
                   the returned URL points to an analytics report for just the specified game.
            started_at:  `str`
                1. REQUIRED: NO; MULTIPLE: NO; DEFAULT: 365 days before the report was issued;
                2. Starting date/time for returned reports, in RFC3339 format with the hours, minutes,
                   and seconds zeroed out and the UTC timezone: YYYY-MM-DDT00:00:00Z.
                   If this is provided, ended_at also must be specified.
                   If started_at is earlier than the default start date, the default date is used.
                   The file contains one row of data per day.
            ended_at: `str`
                1. REQUIRED: NO; MULTIPLE: NO; DEFAULT: 1-2 days before the request was issued;
                2. Ending date/time for returned reports, in RFC3339 format with the hours, minutes,
                   and seconds zeroed out and the UTC timezone: YYYY-MM-DDT00:00:00Z.
                   The report covers the entire ending date; e.g., if 2018-05-01T00:00:00Z is specified,
                   the report covers up to 2018-05-01T23:59:59Z.If this is provided, started_at also must be specified.
                   If ended_at is later than the default end date, the default date is used.
            type: `str`
                1. REQUIRED: NO; MULTIPLE: NO; VALID VALUES: 'overview_v2';
                2. Type of analytics report that is returned.
                   Currently, this field has no affect on the response as there is only one report type.
                   If additional types were added, using this field would return only the URL for the specified report.

        Yields:
        ----------
            `dict` {
                'game_id': `str`
                    ID of the game whose analytics data is being provided.
                'URL': `str`
                    URL to the downloadable CSV file containing analytics data. Valid for 5 minutes.
                'type': `str`
                    Type of report.
                'date_range': `dict` {
                    'started_at': `str`
                        Report start date/time.
                    'ended_at': `str`
                        Report end date/time.
                }
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        async for game_analytics in self.do_paginated_request_by_name('get_game_analytics', locals(), limit):
            yield game_analytics

    async def get_bits_leaderboard(
            self,
            limit: int,
            period: str = None,
            started_at: str = None,
            user_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Yields ranked Bits leaderboard information for an authorized broadcaster.

        1. SCOPE: 'bits:read'
        2. TOKEN: OAuth token required

        Args:
        ----------
            limit: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. limit on number of yields, 0 - unlimited
            user_id: `str`
                1. REQUIRED: NO; MULTIPLE: YES NO; VALID VALUES: values; DEFAULT: default;
                2. ID of the user whose results are returned; i.e., the person who paid for the Bits.
                   As long as `limit` is greater than 1, the returned data includes additional users,
                   with Bits amounts above and below the user specified by user_id.
                   If `user_id` is not provided, the endpoint returns the Bits leaderboard data across top users.
            started_at: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Timestamp for the period over which the returned data is aggregated. Must be in RFC 3339 format.
                   If this is not provided, data is aggregated over the current period;
                   e.g., the current day/week/month/year. This value is ignored if period is "all".
                   The HH:MM:SS part of this value is used only to identify a given day in PST and otherwise ignored
                   For example, if the started_at value resolves to 5PM PST yesterday and period is "day",
                   data is returned for all of yesterday.
            period: `str`
                1. REQUIRED: NO; MULTIPLE: NO; VALID VALUES: 'day', 'week', 'month', 'year', 'all'; DEFAULT: 'all';
                2. Time period over which data is aggregated (PST time zone).This parameter interacts with started_at.

        Yields:
        ----------
            `dict` {
                'rank': `int`
                    Leaderboard rank of the user.
                'score': `int`
                    Leaderboard score (number of Bits) of the user.
                'user_id': `str`
                    ID of the user (viewer) in the leaderboard entry.
                'user_login': `str`
                    User login name.
                'user_name': `str`
                    Display name corresponding to user_id.
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        max_count: int = 100
        count: int = min(limit, max_count)
        async for bits_leader in self.do_paginated_request_by_name('get_bits_leaderboard', locals(), limit):
            yield bits_leader

    async def get_cheermotes(
            self,
            limit: int,
            broadcaster_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Yields available Cheermotes, animated emotes to which viewers can assign Bits, to cheer in chat.
        Cheermotes returned are available throughout Twitch, in all Bits-enabled channels.

        1. SCOPE: NO
        2. TOKEN: OAuth or App Access Token required.

        Args:
        ----------
            limit: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. limit on number of yields, 0 - unlimited
            broadcaster_id: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. ID for the broadcaster who might own specialized Cheermotes.

        Yields:
        ----------
            dict {
                'prefix': `str`
                    The string used to Cheer that precedes the Bits amount.
                'type': `str`
                    Shows whether the emote is global_first_party,  global_third_party, channel_custom, display_only,
                    or sponsored.
                'order': `int`
                    Order of the emotes as shown in the bits card, in ascending order.
                'last_updated': `str`
                    The data when this Cheermote was last updated.
                'is_charitable': `bool`
                     Indicates whether or not this emote provides a charity contribution match during charity campaigns.
                'tiers': `dict` {
                    'min_bits': `int`
                        Minimum number of bits needed to be used to hit the given tier of emote.
                    'id': `str`
                        ID of the emote tier. Possible tiers are: 1,100,500,1000,5000, 10k, or 100k.
                    'color': `str`
                        Hex code for the color associated with the bits of that tier.
                        Grey, Purple, Teal, Blue, or Red color to match the base bit type.
                    'can_cheer': `bool`
                        Indicates whether or not emote information is accessible to users.
                    'show_in_bits_card': `bool`
                        Indicates whether or not we hide the emote from the bits card.
                    'images': {
                        'dark': {
                            'animated': {
                                '1': `str`
                                    1x scale of image (i guess)
                                '1.5': `str`
                                    1.5x scale of image (i guess)
                                '2': `str`
                                    2x scale of image (i guess)
                                '3': `str`
                                    3x scale of image (i guess)
                                '4': `str`
                                    4x scale of image (i guess)
                            }

                            'static': {
                                <↑same_with↑>
                            }
                        }

                        'light': {
                            'animated': {
                                <↑same_with↑>
                            }

                            'static':{
                                <↑same_with↑>
                            }
                        }
                    }
                }
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
        """
        async for cheermote in self.do_paginated_request_by_name('get_cheermotes', locals(), limit):
            yield cheermote

    async def get_extension_transactions(
            self,
            limit: int,
            extension_id: str,
            transaction_id: Union[Iterable[str], str] = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Get Extension Transactions allows extension back end servers to fetch a list of transactions
        that have occurred for their extension across all of Twitch.
        A transaction is a record of a user exchanging Bits for an in-Extension digital good.

        1. SCOPE: NO
        2. TOKEN: OAuth or App Access Token required.

        Args:
        ----------
            limit: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. limit on number of yields, 0 - unlimited
            extension_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. ID of the extension to list transactions for. Maximum: 1
            transaction_id: Union[Iterable[`str`], `str`]
                1. REQUIRED: NO; MULTIPLE: YES;
                2. Transaction IDs to look up. Can include multiple to fetch multiple transactions in a single request.

        Yields:
        ----------
            `dict` {
                'id': `str`
                    Unique identifier of the Bits in Extensions Transaction.
                'timestamp': `str`
                    UTC timestamp when this transaction occurred.
                'broadcaster_id': `str`
                    Twitch User ID of the channel the transaction occurred on.
                'broadcaster_name': `str`
                    Twitch Display Name of the broadcaster.
                'user_id': `str`
                    Twitch User ID of the user who generated the transaction.
                'user_login': `str`
                    Login name of the user who generated the transaction.
                'user_name': `str`
                    Twitch Display Name of the user who generated the transaction.
                'product_type': `str`
                    Enum of the product type. Currently only 'BITS_IN_EXTENSION'.
                'product_data': `dict` {
                    'sku': `str`
                        Unique identifier for the product across the extension.
                    'displayName': `str`
                        Display Name of the product.
                    'inDevelopment': `bool`
                        Flag used to indicate if the product is in development. Either true or false.
                    'cost': `dict` {
                        'amount': `int`
                            Number of Bits required to acquire the product.
                        'type': `str`
                            Always the string
                    }
                }
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
        """
        id = transaction_id
        async for transaction in self.do_paginated_request_by_name('get_extension_transactions', locals(), limit):
            yield transaction

    async def get_channel_information(
            self,
            limit: int,
            broadcaster_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        |Coroutine|\n
        Gets channel information for users.\n
        No REQUIRED scope

        Args:
        ================
            broadcaster_id: REQUIRED `str`
                ID of the channel.

        Returns:
        ================
            `dict` {
                'broadcaster_id': `str`
                    Twitch User ID of this channel owner

                'broadcaster_name': `str`
                    Twitch user display name of this channel owner

                'game_name': `str`
                    Name of the game being played on the channel

                'game_id': `int`
                    Current game ID being played on the channel

                'broadcaster_language': `str`
                    Language of the channel.
                    A language value is either the ISO 639-1 two-letter code for a supported stream language or “other”.

                'title': `str`
                    Title of the stream
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for information in self.do_paginated_request_by_name('get_channel_information', locals(), limit):
            yield information

    async def modify_channel_information(
            self,
            broadcaster_id: str = None,
            game_id: str = None,
            broadcaster_language: str = None,
            title: str = None
    ) -> None:
        """
        |Coroutine|\n
        Modifies channel information for users.\n
        REQUIRED scope: 'user:edit:broadcast'

        Args:
        ================
            broadcaster_id: REQUIRED `str`
                ID of the channel to be updated.

            game_id: REQUIRED `str`
                The current game ID being played on the channel

            broadcaster_language: REQUIRED `str`
                The language of the channel. A language value must be either the ISO 639-1
                two-letter code for a supported stream language or “other”.

            title: REQUIRED `str`
                The title of the stream

        Returns:
        ================
            None:
                successfully modified, else - raises HTTPError exception.

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 204, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        return await self.do_single_request_by_name('modify_channel_information', locals())

    async def get_channel_editors(
            self,
            limit: int,
            broadcaster_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Yields  users who have editor permissions for a specific channel.\n
        REQUIRED scope 'channel:read:editors'

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: `str`
                Broadcaster’s user ID associated with the channel.
        ----------------

        Yields:
        ================
            `dict` {
                'user_id': `str`
                    User ID of the editor.

                'user_name': `str`
                    Display name of the editor.

                'created_at': `str`
                    Date and time the editor was given editor permissions.
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        ----------------
        """
        async for editor in self.do_paginated_request_by_name('get_channel_editors', locals(), limit):
            yield editor

    async def create_custom_rewards(
            self,
            broadcaster_id: str,
            title: str,
            cost: int,
            prompt: str = None,
            is_enabled: bool = None,
            background_color: str = None,
            is_user_input_required: bool = None,
            is_max_per_stream_enabled: bool = None,
            max_per_stream: int = None,
            is_max_per_user_per_stream_enabled: bool = None,
            max_per_user_per_stream: int = None,
            is_global_cooldown_enabled: bool = None,
            global_cooldown_seconds: int = None,
            should_redemptions_skip_request_queue: bool = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Coroutine|

        Creates a Custom Reward on a channel.

        1. SCOPE: 'channel:manage:redemptions'
        2. TOKEN: Query parameter broadcaster_id must match the user_id in the User-Access token

        Args:
        ----------
            broadcaster_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. Provided broadcaster_id must match the user_id in the auth token.
            title: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. The title of the reward
            cost: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. The cost of the reward
            prompt: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The prompt for the viewer when they are redeeming the reward
            is_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Is the reward currently enabled, if false the reward won’t show up to viewers. Defaults true
            max_per_stream: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The maximum number per stream if enabled
            background_color: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Custom background color for the reward. Format: Hex with # prefix. Example: #00E5CB.
            is_user_input_required: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;  DEFAULT: false;
                2. Does the user need to enter information when redeeming the reward.
            max_per_user_per_stream: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The maximum number per user per stream if enabled
            global_cooldown_seconds: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The cooldown in seconds if enabled
            is_max_per_stream_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;  DEFAULT: false;
                2. Whether a maximum per stream is enabled.
            is_global_cooldown_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;  DEFAULT: false;
                2. Whether a cooldown is enabled.
            is_max_per_user_per_stream_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;  DEFAULT: false;
                2. Whether a maximum per user per stream is enabled.
            should_redemptions_skip_request_queue: `bool`
                1. REQUIRED: NO; MULTIPLE: NO; DEFAULT: false;
                2. Should redemptions be set to FULFILLED status immediately when redeemed
                   and skip the request queue instead of the normal UNFULFILLED status.

        Returns:
        ----------
            `dict` {
                'id': `str`
                    ID of the reward
                'broadcaster_id': `str`
                    ID of the channel the reward is for'
                'broadcaster_login': `str`
                    Broadcaster’s user login name.
                'broadcaster_name': `str`
                    Display name of the channel the reward is for
                'title':  `str`
                    The title of the reward
                'cost': REQUIRED `int`
                    The cost of the reward
                'prompt': `str`
                    The prompt for the viewer when they are redeeming the reward
                'is_enabled': `bool`
                    Is the reward currently enabled, if false the reward won’t show up to viewers. Defaults true
                'is_paused': `bool`
                    Is the reward currently paused, if true viewers can’t redeem
                'is_in_stock': `bool`
                    Is the reward currently in stock, if false viewers can’t redeem
                'is_user_input_required': `bool`
                    Does the user need to enter information when redeeming the reward
                'background_color': `str`
                    Custom background color for the reward. Format: Hex with # prefix. Example: #00E5CB.
                'should_redemptions_skip_request_queue': `bool`
                    Should redemptions be set to FULFILLED status immediately when redeemed
                    and skip the request queue instead of the normal UNFULFILLED status. Defaults false
                'redemptions_redeemed_current_stream': Optional[`int`]
                    The number of redemptions redeemed during the current live stream.
                    Counts against the max_per_stream_setting limit.
                    Null if the broadcasters stream isn’t live or max_per_stream_setting isn’t enabled.
                'cooldown_expires_at': Optional[`str`]
                    Timestamp of the cooldown expiration. Null if the reward isn’t on cooldown.
                'max_per_stream_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'max_per_stream': `int`
                        The maximum number per stream if enabled, else - 0
                }

                'max_per_user_per_stream_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'max_per_user_per_stream': `int`
                        The maximum number per user per stream if enabled, else - 0
                }

                'global_cooldown_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'global_cooldown_seconds': `int`
                        The cooldown in seconds if enabled, else - 0
                }

                'image': Optional[`dict`] {
                    'url_1x': `str`,
                        url for 1x image
                    'url_2x': `str`,
                        url for 2x image
                    'url_4x': `str`
                        url for 4x image
                }, can be null if no images are uploaded.

                'default_image': `dict` {
                    'url_1x': `str`,
                        url for 1x image
                    'url_2x': `str`,
                        url for 2x image
                    'url_4x': `str`
                        url for 4x image
                }, Set of default images of 1x, 2x and 4x sizes for the reward.
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        return await self.do_single_request_by_name('create_custom_rewards', locals())

    async def delete_custom_reward(
            self,
            broadcaster_id: str,
            reward_id: str
    ) -> None:
        """
        |Coroutine|

        Deletes a Custom Reward on a channel.
        Only rewards created by the same client_id can be deleted.
        Any UNFULFILLED Custom Reward Redemptions of the deleted Custom Reward will be updated to the FULFILLED status

        1. SCOPE: 'channel:manage:redemptions'
        2. TOKEN: Query parameter broadcaster_id must match the user_id in the User Access token

        Args:
        ----------
            broadcaster_id: REQUIRED `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. Provided `broadcaster_id` must match the `user_id` in the auth token.
            reward_id: REQUIRED `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. ID of the Custom Reward to delete, must match a Custom Reward on `broadcaster_id`’s channel.

        Returns:
        ----------
            `None`

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        id = reward_id
        return await self.do_single_request_by_name('delete_custom_reward', locals())

    async def get_custom_reward(
            self,
            limit: int,
            broadcaster_id: str,
            reward_id: Union[Iterable[str], str] = None,
            only_manageable_rewards: bool = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Yields Custom Reward objects for the Custom Rewards on a channel.
        Developers only have access to update and delete rewards that the same/calling client_id created.

        1. SCOPE: 'channel:read:redemptions'
        2. TOKEN: Query parameter broadcaster_id must match the user_id in the User Access token

        Args:
        ----------
            limit: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. limit on number of yields, 0 - unlimited
            broadcaster_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. Provided broadcaster_id must match the user_id in the auth token.
            reward_id: Union[`str`, Iterable[`str`]]
                1. REQUIRED: NO; MULTIPLE: YES;
                2. When used, this parameter filters the results and only returns reward objects
                   for the Custom Rewards with matching ID. Maximum: 50
            only_manageable_rewards: `bool`
                1. REQUIRED: NO; MULTIPLE: NO; DEFAULT: false;
                2. When set to true, only returns custom rewards that the calling client_id can manage.

        Yields:
        ----------
            `dict` {
                'id': `str`
                    ID of the reward
                'broadcaster_id': `str`
                    ID of the channel the reward is for
                'broadcaster_login': `str`
                    Login of the channel the reward is for
                'broadcaster_name': `str`
                    Display name of the channel the reward is for
                'title':  `str`
                    The title of the reward
                'cost': REQUIRED `int`
                    The cost of the reward
                'prompt': `str`
                    The prompt for the viewer when they are redeeming the reward
                'is_enabled': `bool`
                    Is the reward currently enabled, if false the reward won’t show up to viewers. Defaults true
                'is_paused': `bool`
                    Is the reward currently paused, if true viewers can’t redeem
                'is_in_stock': `bool`
                    Is the reward currently in stock, if false viewers can’t redeem
                'is_user_input_required': `bool`
                    Does the user need to enter information when redeeming the reward
                'background_color': `str`
                    Custom background color for the reward. Format: Hex with # prefix. Example: #00E5CB.
                'should_redemptions_skip_request_queue': `bool`
                    Should redemptions be set to FULFILLED status immediately when redeemed
                    and skip the request queue instead of the normal UNFULFILLED status. Defaults false
                'redemptions_redeemed_current_stream': Optional[`int`]
                    The number of redemptions redeemed during the current live stream.
                    Counts against the max_per_stream_setting limit.
                    Null if the broadcasters stream isn’t live or max_per_stream_setting isn’t enabled.
                'cooldown_expires_at': Optional[`str`]
                    Timestamp of the cooldown expiration. Null if the reward isn’t on cooldown.
                'max_per_stream_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'max_per_stream': `int`
                        The maximum number per stream if enabled, else - 0
                }

                'max_per_user_per_stream_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'max_per_user_per_stream': `int`
                        The maximum number per user per stream if enabled, else - 0
                }

                'global_cooldown_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled

                    'global_cooldown_seconds': `int`
                        The cooldown in seconds if enabled, else - 0
                }

                'image': Optional[`dict`] {
                    'url_1x': `str`,
                        url for 1x image
                    'url_2x': `str`,
                        url for 2x image
                    'url_4x': `str`
                        url for 4x image
                }, can be null if no images have been uploaded.

                'default_image': `dict` {
                    'url_1x': `str`,
                        url for 1x image
                    'url_2x': `str`,
                        url for 2x image
                    'url_4x': `str`
                        url for 4x image
                }, Set of default images of 1x, 2x and 4x sizes for the reward.
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        id = reward_id
        async for reward in self.do_paginated_request_by_name('get_custom_reward', locals(), limit):
            yield reward

    async def get_custom_reward_redemption(
            self,
            limit: int,
            broadcaster_id: str,
            reward_id: str,
            redemption_id: Union[Iterable[str], str] = None,
            status: str = None,
            sort: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |AsyncGenerator|

        Yields Custom Reward Redemption objects for a Custom Reward on a channel that was created by the same client_id
        Developers only have access to get and update redemptions for the rewards they created.

        1. SCOPE: 'channel:read:redemptions'
        2. TOKEN: Parameter broadcaster_id must match the user_id in the User Access token

        Args:
        ----------
            limit: `int`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. limit on number of yields, 0 - unlimited
            broadcaster_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. Provided broadcaster_id must match the user_id in the auth token.
            reward_id: `str`
                1. REQUIRED: YES; MULTIPLE: YES NO;
                2. When ID is not provided, this parameter returns paginated Custom Reward Redemption objects
                   for redemptions of the Custom Reward with ID reward_id
            redemption_id: Union[Iterable[str], str]
                1. REQUIRED: NO; MULTIPLE: YES;
                2. When used, this param filters the results and only returns Custom Reward Redemption objects
                   or the redemptions with matching ID. Maximum: 50
            status: `str`
                1. REQUIRED: NO; MULTIPLE: NO; VALID VALUES: 'UNFULFILLED', 'FULFILLED' or 'CANCELED';
                2. When `redemption_id` is not provided, this param is required
                   and filters the paginated Custom Reward Redemption objects for redemptions with the matching status.
            sort: `str`
                1. REQUIRED: NO; MULTIPLE: NO; VALID VALUES: 'OLDEST', 'NEWEST'; DEFAULT: OLDEST;
                2. order of redemptions returned when getting the paginated Custom Reward Redemption objects for reward.

        Yields:
        ----------
            `dict` {
                'id': `str`
                    The ID of the redemption.
                'broadcaster_id': `str`
                    The id of the broadcaster that the reward belongs to.
                'broadcaster_login': `str`
                    Broadcaster’s user login name.
                'broadcaster_name': `str`
                    The display name of the broadcaster that the reward belongs to.
                'user_id': `str`
                    The ID of the user that redeemed the reward
                'user_login': `str`
                    The login of the user who redeemed the reward.
                'user_name': `str`
                    The display name of the user that redeemed the reward.
                'user_input':  `str`
                    The user input provided. Empty string if not provided.
                'status': `str`
                    One of UNFULFILLED, FULFILLED or CANCELED
                'redeemed_at': `str`
                    RFC3339 timestamp of when the reward was redeemed.
                'reward': `dict` {
                    'id': `str`,
                        ID of reward
                    'title': `str`,
                        title of reward
                    'prompt': `str`
                        prompt of reward
                    'cost': `int`
                        cost of reward
                }
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        id = redemption_id
        async for redemption in self.do_paginated_request_by_name('get_custom_reward_redemption', locals(), limit):
            yield redemption

    async def update_custom_reward(
            self,
            broadcaster_id: str,
            reward_id: str,
            title: str = None,
            cost: int = None,
            prompt: str = None,
            is_paused: bool = None,
            is_enabled: bool = None,
            max_per_stream: int = None,
            background_color: str = None,
            is_user_input_required: bool = None,
            max_per_user_per_stream: int = None,
            global_cooldown_seconds: int = None,
            is_max_per_stream_enabled: bool = None,
            is_global_cooldown_enabled: bool = None,
            is_max_per_user_per_stream_enabled: bool = None,
            should_redemptions_skip_request_queue: bool = None
    ) -> dict:
        """
        |Coroutine|

        Updates a Custom Reward created on a channel.
        Only rewards created by the same client_id can be updated.

        1. SCOPE: 'channel:manage:redemptions'
        2. TOKEN: Parameter broadcaster_id must match the user_id in the User Access token

        Args:
        ----------
            broadcaster_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. Provided broadcaster_id must match the user_id in the auth token.
            reward_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. ID of the Custom Reward to update, must match a Custom Reward on broadcaster_id’s channel.
            title: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The title of the reward
            cost: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The cost of the reward
            prompt: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The prompt for the viewer when they are redeeming the reward
            is_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Is the reward currently enabled, if false the reward won’t show up to viewers
            is_paused: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Is the reward currently paused, if true viewers can’t redeem
            max_per_stream: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The maximum number per stream if enabled
            background_color: `str`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Custom background color for the reward. Format: Hex with # prefix. Example: #00E5CB.
            is_user_input_required: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Does the user need to enter information when redeeming the reward.
            max_per_user_per_stream: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The maximum number per user per stream if enabled
            global_cooldown_seconds: `int`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. The cooldown in seconds if enabled
            is_max_per_stream_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Whether a maximum per stream is enabled
            is_global_cooldown_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Whether a cooldown is enabled.
            is_max_per_user_per_stream_enabled: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Whether a maximum per user per stream is enabled.
            should_redemptions_skip_request_queue: `bool`
                1. REQUIRED: NO; MULTIPLE: NO;
                2. Should redemptions be set to FULFILLED status immediately when redeemed
                   and skip the request queue instead of the normal UNFULFILLED status.

        Returns:
        ----------
            `dict` {
                'id': `str`
                    ID of the reward
                'broadcaster_id': `str`
                    ID of the channel the reward is for
                'broadcaster_login': `str`
                    Broadcaster’s user login name.
                'broadcaster_name': `str`
                    Display name of the channel the reward is for
                'title':  `str`
                    The title of the reward
                'cost': REQUIRED `int`
                    The cost of the reward
                'prompt': `str`
                    The prompt for the viewer when they are redeeming the reward
                'background_color': `str`
                    Custom background color for the reward. Format: Hex with # prefix. Example: #00E5CB.
                'is_paused': `bool`
                    Is the reward currently paused, if true viewers can’t redeem
                'is_enabled': `bool`
                    Is the reward currently enabled, if false the reward won’t show up to viewers. Defaults true
                'is_in_stock': `bool`
                    Is the reward currently in stock, if false viewers can’t redeem
                'is_user_input_required': `bool`
                    Does the user need to enter information when redeeming the reward
                'should_redemptions_skip_request_queue': `bool`
                    Should redemptions be set to FULFILLED status immediately when redeemed
                    and skip the request queue instead of the normal UNFULFILLED status. Defaults false
                'redemptions_redeemed_current_stream': Optional[`int`]
                    The number of redemptions redeemed during the current live stream.
                    Counts against the max_per_stream_setting limit.
                    Null if the broadcasters stream isn’t live or max_per_stream_setting isn’t enabled.
                'cooldown_expires_at': Optional[`str`]
                    Timestamp of the cooldown expiration. Null if the reward isn’t on cooldown.
                'max_per_stream_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'max_per_stream': `int`
                        The maximum number per stream if enabled, else - 0
                }

                'max_per_user_per_stream_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'max_per_user_per_stream': `int`
                        The maximum number per user per stream if enabled, else - 0
                }

                'global_cooldown_setting': `dict` {
                    'is_enabled': `bool`
                        marks if this enabled
                    'global_cooldown_seconds': `int`
                        The cooldown in seconds if enabled, else - 0
                }

                'image': Optional[`dict`] {
                    'url_1x': `str`,
                        url for 1x image
                    'url_2x': `str`,
                        url for 2x image
                    'url_4x': `str`
                        url for 4x image
                }, can be null if no images have been uploaded.

                'default_image': `dict` {
                    'url_1x': `str`,
                        url for 1x image
                    'url_2x': `str`,
                        url for 2x image
                    'url_4x': `str`
                        url for 4x image
                }, Set of default images of 1x, 2x and 4x sizes for the reward.
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        id = reward_id
        return await self.do_single_request_by_name('update_custom_reward', locals())

    async def update_redemption_status(
            self,
            broadcaster_id: str,
            reward_id: str,
            redemption_id: Union[Iterable[str], str],
            status: str
    ) -> dict:
        """
        |Coroutine|

        Updates the status of Custom Reward Redemption objects on a channel that are in the UNFULFILLED status.
        Only redemptions for a reward created by the same client_id as attached to the access token can be updated.

        1. SCOPE: 'channel:manage:redemptions'
        2. TOKEN: Parameter broadcaster_id must match the user_id in the User-Access token

        Args:
        ----------
            broadcaster_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO; 2. MULTIPLE
                2. Provided broadcaster_id must match the user_id in the auth token.
            reward_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. ID of the Custom Reward to update, must match a Custom Reward on broadcaster_id’s channel.
            redemption_id: `Union[Iterable[str], str]`
                1. REQUIRED: YES; MULTIPLE: YES;
                2. ID of the Custom Reward Redemption to update,
                   must match a Custom Reward Redemption on broadcaster_id’s channel Max: 50
            status: `str`
                1. REQUIRED: YES; MULTIPLE: NO; VALID VALUES: 'FULFILLED', 'CANCELED';
                2. The new status to set redemptions to. Updating to CANCELED will refund the user their points.

        Returns:
        ----------
            `dict` {
                'id': `str`
                    The ID of the redemption.
                'broadcaster_id': `str`
                    The id of the broadcaster that the reward belongs to.
                'broadcaster_login': `str`
                    Broadcaster’s user login name.
                'broadcaster_name': `str`
                    The display name of the broadcaster that the reward belongs to.
                'user_id': `str`
                    The ID of the user that redeemed the reward
                'user_login': `str`
                    The login of the user that redeemed the reward.
                'user_name': `str`
                    The display name of the user that redeemed the reward.
                'user_input':  `str`
                    The user input provided. Empty string if not provided.
                'status': `str`
                    One of UNFULFILLED, FULFILLED or CANCELED
                'redeemed_at': `str`
                    RFC3339 timestamp of when the reward was redeemed.
                'reward': `dict` {
                    'id': `str`,
                        ID of reward
                    'title': `str`,
                        title of reward
                    'prompt': `str`
                        prompt of reward
                    'cost': `int`
                        cost of reward
                }
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        id = redemption_id
        return await self.do_single_request_by_name('update_redemption_status', locals())

    async def create_clip(
            self,
            broadcaster_id: str,
            has_delay: bool = None
    ) -> dict:
        """
        |Coroutine|

        Creates a clip programmatically. This returns both an ID and an edit URL for the new clip.
        Clip creation takes time. We recommend that you query Get Clips, with the clip ID that is returned here.
        If Get Clips returns a valid clip, your clip creation was successful.
        If, after 15 seconds, you still have not gotten back a valid clip from Get Clips,
        assume that the clip was not created and retry Create Clip.

        1. SCOPE: 'clips:edit'
        2. TOKEN: OAuth token required

        Args:
        ----------
            broadcaster_id: `str`
                1. REQUIRED: YES; MULTIPLE: NO;
                2. ID of the stream from which the clip will be made.
            has_delay: `bool`
                1. REQUIRED: NO; MULTIPLE: NO; DEFAULT: False;
                2. If false, the clip is captured from the live stream when the API is called;
                   otherwise, a delay is added before the clip is captured (to account for the brief delay between
                   the broadcaster’s stream and the viewer’s experience of that stream)

        Returns:
        ----------
            `dict` {
                'id': `str`
                    ID of the clip that was created.
                'edit_url': `str`
                    URL of the edit page for the clip.
            }

        Raises:
            `HTTPError`:
                if status-code of response is not 2XX, passes response.
            `AccessError`:
                if the Token has not required scope.
        """
        return await self.do_single_request_by_name('create_clip', locals())

    async def get_clips(
            self,
            limit: int,
            broadcaster_id: str = None,
            game_id: str = None,
            clip_id: Union[Iterable[str], str] = None,
            started_at: str = None,
            ended_at: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Yields clip information by clip ID (one or more), broadcaster ID (one only), or game ID (one only).\n
        For a query to be valid, clip_id (one or more), broadcaster_id, or game_id must be specified.
        You may specify only one of these parameters.\n
        No REQUIRED scope

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: `str`
                ID of the broadcaster for whom clips are returned.

            game_id: `str`
                ID of the game for which clips are returned.

            clip_id: Union[`str`, Iterable[`str`]]
                ID of the clip being queried. Limit: 100.

            started_at: `str`
                Starting date/time for returned clips, in RFC3339 format. (The seconds value is ignored.)
                If this is specified, ended_at also should be specified; otherwise,
                the ended_at date/time will be 1 week after the started_at value.

            ended_at: `str`
                Ending date/time for returned clips, in RFC3339 format. (Note that the seconds value is ignored.)
                If this is specified, started_at also must be specified; otherwise, the time period is ignored.
        ----------------

        Yields:
        ================
            `dict` {
                'id': `str`
                    ID of the clip being queried.

                'broadcaster_id': `str`
                    User ID of the stream from which the clip was created.

                'broadcaster_name': `str`
                    Display name corresponding to broadcaster_id.

                'creator_id':  `str`
                    ID of the user who created the clip.

                'creator_name': REQUIRED `str`
                    Display name corresponding to creator_id.

                'created_at': `str`
                    Date when the clip was created.

                'video_id': `str`
                    ID of the video from which the clip was created.

                'game_id': `str`
                    ID of the game assigned to the stream when the clip was created.

                'language': `str`
                    Language of the stream from which the clip was created.
                    A language value is either the ISO 639-1 two-letter code for a supported stream language or “other”.

                'title': `str`
                    Title of the clip.

                'view_count': `int`
                    Number of times the clip has been viewed.

                'url': `bool`
                    URL where the clip can be viewed.

                'embed_url': str
                    URL to embed the clip.

                'thumbnail_url': str
                    URL of the clip thumbnail.
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        ----------------
        """
        id = clip_id
        async for clip in self.do_paginated_request_by_name('get_clips', locals(), limit):
            yield clip

    async def get_code_status(
            self,
            limit: int,
            code: Union[Iterable[str], str],
            user_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Gets the status of one or more provided codes. This API requires that the caller is an authenticated Twitch user
        The API is throttled to one request per second per authenticated user.
        Codes are redeemable alphanumeric strings tied only to the bits product.
        This third-party API allows other parties to redeem codes on behalf of users.
        Third-party app and extension developers can use the API to provide rewards of bits from within their games.\n
        We provide sets of codes to the third party as part of a contract agreement.
        The third-party program then calls this API to credit a Twitch user by submitting any specific codes.
        This means that a bits reward can be applied without users having to follow any manual steps.\n
        All codes are single-use. Once a code has been redeemed, via either this API or the site page,
        then the code is no longer valid for any further use.

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            code: REQUIRED Union[`str`, Iterable[`str`]]
                The code to get the status of.
                Repeat this query parameter additional times to get the status of multiple codes.
                1-20 code parameters are allowed.

            user_id: REQUIRED `str`
                Represents a numeric Twitch user ID.
                The user account which is going to receive the entitlement associated with the code.
        ----------------

        Yields:
        ================
            `dict` {
                'code': `str`
                    code

                'status ': `str`
                    status of code, see Notes
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        ----------------

        Notes:
        ================
            Code Statuses:
                'SUCCESSFULLY_REDEEMED':
                    Request successfully redeemed this code to the authenticated user’s account.
                    This status will only ever be encountered when calling the POST API to redeem a key.

                'ALREADY_CLAIMED':
                    Code has already been claimed by a Twitch user.

                'EXPIRED':
                    Code has expired and can no longer be claimed.

                'USER_NOT_ELIGIBLE':
                    User is not eligible to redeem this code.

                'NOT_FOUND':
                    Code is not valid and/or does not exist in our database.

                'INACTIVE':
                    Code is not currently active.

                'UNUSED':
                    Code has not been claimed.
                    This status will only ever be encountered when calling the GET API to get a keys status.

                'INCORRECT_FORMAT':
                    Code was not properly formatted.

                'INTERNAL_ERROR':
                    Indicates some internal and/or unknown failure handling this code.
        ----------------
        """
        async for status in self.do_paginated_request_by_name('get_code_status', locals(), limit):
            yield status

    async def get_drops_entitlements(
            self,
            limit: int,
            entitlement_id: str = None,
            user_id: str = None,
            game_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Gets a list of entitlements for a given organization that have been granted to a game, user, or both.\n
        OAuth Token Client ID must have ownership of Game:\n
        Client ID > RBAC Organization ID > Game ID

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            entitlement_id: Union[`str`, Iterable[`str`]]
                Unique Identifier of the entitlement

            user_id: `str`
                A Twitch User ID

            game_id: `str`
                A Twitch Game ID
        ----------------

        Yields:
        ================
            `dict` {
                'id': `str`
                    Unique Identifier of the entitlement

                'benefit_id ': `str`
                    Identifier of the Benefit

                'timestamp ': `str`
                    UTC timestamp in ISO format when this entitlement was granted on Twitch.

                'user_id ': `str`
                    Twitch User ID of the user who was granted the entitlement.

                'game_id ': `str`
                    Twitch Game ID of the game that was being played when this benefit was entitled.
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        ----------------

        Notes:
        ================
            `User OAuth Token` can use empety params or only `game_id`

            `App Access OAuth Token` can use all combinations of params
        ----------------
        """
        id = entitlement_id
        async for entitlement in self.do_paginated_request_by_name('get_drops_entitlements', locals(), limit):
            yield entitlement

    async def redeem_code(
            self,
            code: Union[Iterable[str], str] = None,
            user_id: str = None
    ) -> List[dict]:
        """
        |Coroutine|
        ================
        Redeems one or more provided codes to the authenticated Twitch user.
        This API requires that the caller is an authenticated Twitch user.
        This API requires that the caller is an authenticated Twitch user.
        The API is throttled to one request per second per authenticated user.
        Codes are redeemable alphanumeric strings tied only to the bits product.
        This third-party API allows other parties to redeem codes on behalf of users.
        Third-party app and extension developers can use the API to provide rewards of bits from within their games.
        We provide sets of codes to the third party as part of a contract agreement.
        The third-party program then calls this API to credit the Twitch user by submitting any specific codes.
        This means that a bits reward can be applied without the user having to follow any manual steps.\n
        All codes are single-use. Once a code has been redeemed, via either this API or the site page,
        the code is no longer valid for any further use

        ----------------

        Args:
        ================
            code: Union[`str`, Optional[`str`]]
                The code to redeem to the authenticated user’s account.
                A fifteen character (plus optional hyphen separators) alphanumeric string, e.g. ABCDE-12345-FGHIJ

            user_id: `str`
                Represents a numeric Twitch user ID.
                The user account which is going to receive the entitlement associated with the code.
        ----------------

        Returns:
        ================
            `list` [
                `dict` {
                    'code': `str`
                        code

                    'status': `str`
                        status of code, see Notes
                },
                ...
            ]
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        ----------------

        Notes:
        ================
            Code Statuses:
                'SUCCESSFULLY_REDEEMED':
                    Request successfully redeemed this code to the authenticated user’s account.
                    This status will only ever be encountered when calling the POST API to redeem a key.

                'ALREADY_CLAIMED':
                    Code has already been claimed by a Twitch user.

                'EXPIRED':
                    Code has expired and can no longer be claimed.

                'USER_NOT_ELIGIBLE':
                    User is not eligible to redeem this code.

                'NOT_FOUND':
                    Code is not valid and/or does not exist in our database.

                'INACTIVE':
                    Code is not currently active.

                'UNUSED':
                    Code has not been claimed.
                    This status will only ever be encountered when calling the GET API to get a keys status.

                'INCORRECT_FORMAT':
                    Code was not properly formatted.

                'INTERNAL_ERROR':
                    Indicates some internal and/or unknown failure handling this code.
        ----------------
        """
        return await self.do_single_request_by_name('redeem_code', locals())

    async def get_top_games(
            self,
            limit: int
    ) -> dict:
        """
        |Async Generator|\n
        Gets games sorted by number of current viewers on Twitch, most popular first.

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

        Yields:
        ================
            `dict` {
                'id': `str`
                    Game ID.

                'box_art_url ': `str`
                    Template URL for a game’s box art.

                'name ': `str`
                    Game name.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for game in self.do_paginated_request_by_name('get_top_games', locals(), limit):
            yield game

    async def get_games(self,
                        limit: int,
                        game_id: Union[Iterable[str], str] = None,
                        name: Union[Iterable[str], str] = None
                        ) -> dict:
        """
        |Async Generator|\n
        Gets game information by game ID or name.\n
        `game_id` and/or `name` must be specified

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            game_id: `str`
                Game ID. At most 100 id values can be specified

            name: `str`
                Game name. The name must be an exact match. For example, “Pokemon” will not return a list of Pokemon games;
                instead, query any specific Pokemon games in which you are interested.
                At most 100 name values can be specified.

        Yields:
        ================
            `dict` {
                'id': `str`
                    Game ID.

                'box_art_url ': `str`
                    Template URL for a game’s box art.

                'name ': `str`
                    Game name.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        id = game_id
        async for game in self.do_paginated_request_by_name('get_games', locals(), limit):
            yield game

    async def create_eventsub_subscription(
            self,
            type: str,
            condition: Dict[str, str],
            callback: str,
            secret: str,
            version: str = '1',
            method: str = 'webhook'
    ):
        transport = {
            'method': method,
            'callback': callback,
            'secret': secret
        }
        return await self.do_single_request_by_name('create_eventsub_subscription', locals())

    async def delete_eventsub_subscription(
            self,
            subscription_id: str
    ):
        id = subscription_id
        return await self.do_single_request_by_name('delete_eventsub_subscription', locals())

    async def get_eventsub_subscriptions(
            self,
            limit: int
    ):
        async for subscription in self.do_paginated_request_by_name('get_eventsub_subscriptions', locals(), limit):
            yield subscription

    async def get_hype_train_events(self,
                                    limit: int,
                                    broadcaster_id: str = None,
                                    event_id: Union[Iterable[str], str] = None
                                    ) -> dict:
        """
        |Async Generator|\n
        Gets the information of the most recent Hype Train of the given channel ID.
        When there is currently an active Hype Train, it returns information about that Hype Train.
        When there is currently no active Hype Train, it returns information about the most recent Hype Train.
        After 5 days, if no Hype Train has been active, the endpoint will return an empty response.\n
        REQUIRED scope: 'channel:read:hype_train'

        Args:
        ================
        limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: REQUIRED `str`
                User ID of the broadcaster. Must match the User ID in the Bearer token if User Token is used.

            event_id: `str`
                The id of the wanted event, if known

        Yields:
        ================
            `dict` {
                'id': `str`
                    The distinct ID of the event

                'event_type': `str`
                    Displays hypetrain.{event_name}, currently only hypetrain.progression

                'event_timestamp': `str`
                    RFC3339 formatted timestamp of event

                'version': `str`
                    Returns the version of the endpoint

                'event_data': `dict` {
                    'id': `str`
                        The distinct ID of this Hype Train

                    'broadcaster_id': `str`
                        Channel ID of which Hype Train events the clients are interested in

                    'cooldown_end_time': `str`
                        RFC3339 formatted timestamp of when another Hype Train can be started again

                    'expires_at': `str`
                        RFC3339 formatted timestamp of the expiration time of this Hype Train

                    'goal': `int`
                        The goal value of the level above

                    'level': `int`
                        The highest level (in the scale of 1-5) reached of the Hype Train

                    'started_at': `str`
                        RFC3339 formatted timestamp of when this Hype Train started

                    'total': `int`
                        The total score so far towards completing the level goal above

                    'last_contribution': `dict` {
                        total': `int`
                            Total amount contributed. If type is BITS, total represents amounts of bits used.
                            If type is SUBS, total is 500, 1000, or 2500
                            to represent tier 1, 2, or 3 subscriptions respectively

                        'type': `str`
                            Identifies the contribution method, either BITS or SUBS

                        'user': `str`
                        ID of the contributing user
                    }, An object that represents the most recent contribution

                    'top_contributions': `list` [
                        `dict` {
                            'total': `int`
                                Total aggregated amount of all contributions by the top contributor.
                                If type is BITS, total represents aggregate amount of bits used.
                                If type is SUBS, aggregate total where 500, 1000, or 2500
                                represent tier 1, 2, or 3 subscriptions respectively.
                                For example, if top contributor has gifted a tier 1, 2, and 3 subscription,
                                total would be 4000.

                            'type': `str`
                                Identifies the contribution method, either BITS or SUBS

                            'user': `str`
                                ID of the contributing user
                        },\n
                        ...
                    ], An array of top contribution objects, one object for each type.
                    For example, one object would represent top contributor of BITS, by aggregate,
                    and one would represent top contributor of SUBS by count.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        id = event_id
        async for event in self.do_paginated_request_by_name('get_hype_train_events', locals(), limit):
            yield event

    async def check_automod_status(
            self,
            data: List[dict],
    ):
        return await self.do_single_request_by_name('check_automod_status', {'data': data})

    async def get_banned_events(self,
                                limit: int,
                                broadcaster_id: str = None,
                                user_id: Union[Iterable[str], str] = None
                                ) -> dict:
        """
        |Async Generator|\n
        Yields user bans and un-bans in a channel.\n
        REQUIRED scope: 'moderation:read'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: REQUIRED `str`
                Provided broadcaster_id must match the user_id in the auth token. Maximum: 1

            user_id: Union[`str`, Iterable[`str`]]
                Filters the results and only returns a status object for ban events that include users being banned
                or un-banned in this channel and have a matching user_id.

        Yields:
        ================
            `dict` {
                'id': `str`
                    Event ID

                'event_type': `str`
                    Displays moderation.user.ban or moderation.user.unban

                'event_timestamp': `str`
                    RFC3339 formatted timestamp for events.

                'version': `str`
                    Returns the version of the endpoint.

                'event_data': `dict` {
                    'broadcaster_id': `str`
                        broadcaster ID

                    'broadcaster_name': `str`
                        broadcaster name

                    'user_id': `str`
                        user ID

                    'user_name': `str`
                        user name

                    'expires_at': `str`
                        expires at
                }
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for event in self.do_paginated_request_by_name('get_banned_events', locals(), limit):
            yield event

    async def get_banned_users(self,
                               limit: int,
                               broadcaster_id: str = None,
                               user_id: Union[Iterable[str], str] = None
                               ) -> dict:
        """
        |Async Generator|\n
        Yields banned and timed-out users in a channel.\n
        REQUIRED scope: 'moderation:read'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: REQUIRED `str`
                Provided broadcaster_id must match the user_id in the auth token. Maximum: 1

            user_id: Union[`str`, Iterable[`str`]]
                Filters the results and only returns a status object for ban events that include users being banned
                or un-banned in this channel and have a matching user_id.

        Yields:
        ================
            `dict` {
                'user_id': `str`
                    User ID of a user who has been banned.

                'user_name': `str`
                    Display name of a user who has been banned.

                'expires_at': `str`
                    RFC3339 formatted timestamp for timeouts; empty string for bans.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for user in self.do_paginated_request_by_name('get_banned_users', locals(), limit):
            yield user

    async def get_moderators(self,
                             limit: int,
                             broadcaster_id: str = None,
                             user_id: Union[Iterable[str], str] = None
                             ) -> dict:
        """
        |Async Generator|\n
        Yields moderators in a channel.\n
        REQUIRED scope: 'moderation:read'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: REQUIRED `str`
                Provided broadcaster_id must match the user_id in the auth token. Maximum: 1

            user_id: Union[`str`, Iterable[`str`]]
                Filters the results and only returns a status object for users
                 who are moderators in this channel and have a matching user_id.

        Yields:
        ================
            `dict` {
                'user_id': `str`
                    User ID of a user who has got moderator status.

                'user_name': `str`
                    Display name of a user who has got moderator status.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for moderator in self.do_paginated_request_by_name('get_moderators', locals(), limit):
            yield moderator

    async def get_moderator_events(self,
                                   limit: int,
                                   broadcaster_id: str = None,
                                   user_id: Union[Iterable[str], str] = None
                                   ) -> dict:
        """
        |Async Generator|\n
        Yields events of moderators or users added and removed as moderators from a channel.\n
        REQUIRED scope: 'moderation:read'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: REQUIRED `str`
                Provided broadcaster_id must match the user_id in the auth token. Maximum: 1

            user_id: Union[`str`, Iterable[`str`]]
                Filters the results and only returns a status object for users
                 who are moderators in this channel and have a matching user_id.

        Yields:
        ================
            `dict` {
                'id': `str`
                    Event ID

                'event_type': `str`
                    Displays `moderation.moderator.add` or `moderation.moderator.remove`

                'event_timestamp': `str`
                    RFC3339 formatted timestamp for events.

                'version': `str`
                    Returns the version of the endpoint.

                'event_data': `dict` {
                    'broadcaster_id': `str`
                        broadcaster ID

                    'broadcaster_name': `str`
                        broadcaster name

                    'user_id': `str`
                        user ID

                    'user_name': `str`
                        user name

                    'expires_at': `str`
                        expires at
                }
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for event in self.do_paginated_request_by_name('get_moderator_events', locals(), limit):
            yield event

    async def search_categories(self, limit: int, query: str) -> dict:
        """
        |Async Generator|\n
        Yields games or categories that match the query via name either entirely or partially.\n
        No REQUIRED scope

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            query: REQUIRED `str`
                URl encoded search query

        Yields:
        ================
            `dict` {
                'box_art_url': `str`
                    Template URL for the game’s box art.

                'name': `str`
                    Game/category name.

                'id': `str`
                    Game/category ID.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for category in self.do_paginated_request_by_name('search_categories', locals(), limit):
            yield category

    async def search_channels(self, limit: int, query: str) -> dict:
        """
        |Async Generator|\n
        Yields channels (users who have streamed within the past 6 months)
        that match the query via channel name or description either entirely or partially.
        Results include both live and offline channels.
        Online channels will have additional metadata (e.g. started_at, tag_ids).\n
        No REQUIRED scope

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            query: REQUIRED `str`
                URl encoded search query

        Yields:
        ================
            `dict` {
                'game_id': `str`
                    ID of the game being played on the stream

                'id': `str`
                    Channel ID

                'display_name': `str`
                    Display name corresponding to user_id

                'broadcaster_language': `str`
                    Channel language (Broadcaster Language field from the Channels service).
                    A language value is either the ISO 639-1 two-letter code for a supported stream language or “other”.

                'title': `str`
                    channel title

                'thumbnail_url': `str`
                    Thumbnail URL of the stream. All image URLs have variable width and height.
                    You can replace {width} and {height} with any values to get that size image.

                'is_live': `bool`
                    Live status

                'started_at': `str`
                    UTC timestamp. (live only)

                'tag_ids': `list` [`str`]
                    Shows tag IDs that apply to the stream (live only).
                    See https://www.twitch.tv/directory/all/tags for tag types
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for channel in self.do_paginated_request_by_name('search_channels', locals(), limit):
            yield channel

    async def get_stream_key(
            self,
            limit: int,
            broadcaster_id: str
    ) -> str:
        """
        |Coroutine|\n
        Gets the channel stream key for a user.\n
        REQUIRED scope: 'channel:read:stream_key'

        Args:
        ================
            broadcaster_id: REQUIRED `str`
                User ID of the broadcaster

        Returns:
        ================
            `str`:
                Stream key for the channel

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for stream_key in self.do_paginated_request_by_name('get_stream_key', locals(), limit):
            yield stream_key

    async def get_streams(
            self,
            limit: int,
            game_id: Union[Iterable[str], str] = None,
            language: Union[Iterable[str], str] = None,
            user_id: Union[Iterable[str], str] = None,
            user_login: Union[Iterable[str], str] = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|\n
        Yields  information about active streams.
        Streams are returned sorted by number of current viewers, in descending order.
        Across multiple pages of results, there may be duplicate or missing streams, as viewers join and leave streams\n
        No REQUIRED scope

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            game_id: `str`
                Returns streams broadcasting a specified game ID. You can specify up to 100 IDs.

            language: `str`
                Stream language. You can specify up to 100 languages.
                A language value must be either the ISO 639-1 two-letter code for a supported stream language or “other”.

            user_id: `str`
                Returns streams broadcast by one or more specified user IDs. You can specify up to 100 IDs.

            user_login: `str`
                Returns streams broadcast by one or more specified user login names. You can specify up to 100 names.

        Yields:
        ================
            `dict` {
                'id': `str`
                    Stream ID.

                'user_id': `str`
                    ID of the user who is streaming.

                'user_name': `str`
                    Display name corresponding to user_id.

                'game_id': `str`
                    ID of the game being played on the stream

                'game_name': `str`
                    Name of the game being played.

                'language': `str`
                    Stream language.
                    A language value is either the ISO 639-1 two-letter code for a supported stream language or “other”.

                'title': `str`
                    Stream title.

                'type': `str`
                    Stream type: "live" or "" (in case of error).

                'thumbnail_url': `str`
                    Thumbnail URL of the stream. All image URLs have variable width and height.
                    You can replace {width} and {height} with any values to get that size image.

                'viewer_count': `int`
                    Number of viewers watching the stream at the time of the query.

                'started_at': `str`
                    UTC timestamp.

                'tag_ids': `list` [`str`]
                    Shows tag IDs that apply to the stream.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for stream in self.do_paginated_request_by_name('get_streams', locals(), limit):
            yield stream

    async def create_stream_marker(
            self,
            user_id: str,
            description: str = None
    ) -> dict:
        """
        |Coroutine|\n
        Gets the channel stream key for a user.\n
        REQUIRED scope: 'channel:read:stream_key'

        Args:
        ================
            user_id: REQUIRED `str`
                ID of the broadcaster in whose live stream the marker is created.

            description: `str`
                Description of or comments on the marker. Max length is 140 characters.

        Returns:
        ================
            `dict` {
                'created_at': `str`
                    RFC3339 timestamp of the marker.

                'description': `str`
                    Description of the marker.

                'id': `str`
                    Unique ID of the marker.

                'position_seconds': `int`
                    Relative offset (in seconds) of the marker, from the beginning of the stream.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        return await self.do_single_request_by_name('create_stream_marker', locals())

    async def get_stream_markers(
            self,
            limit: int,
            user_id: str = None,
            video_id: str = None
    ) -> dict:
        """
        |Async Generator|\n
        Yields markers for either a specified user’s most recent stream or a specified VOD/video (stream),
        ordered by recency. A marker is an arbitrary point in a stream that the broadcaster wants to mark; e.g.,
        to easily return to later.
        The only markers returned are those created by the user identified by the Bearer token.\n
        Only one of user_id and video_id must be specified.\n
        REQUIRED scope: 'user:read:broadcast'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            user_id: `str`
                ID of the broadcaster from whose stream markers are returned.

            video_id: `str`
                ID of the VOD/video whose stream markers are returned.

            Yields:(differ of twitch-API)\n
            `dict` {
                'id': `str`
                    ID of the marker.

                'created_at': `str`
                    RFC3339 timestamp of the marker.

                'description': `str`
                    Description of the marker.

                'position_seconds': `int`
                    Relative offset (in seconds) of the marker, from the beginning of the stream.

                'URL': `str`
                    A link to the stream with a query parameter that is a timestamp of the marker's location.

                'user_id': `str`
                    ID of the user whose markers are returned.

                'user_name': `str`
                    Display name corresponding to user_id.

                'video_id': `str`
                    ID of the stream (VOD/video) that was marked.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for marker in self.do_paginated_request_by_name('get_stream_markers', locals(), limit):
            yield marker

    async def get_broadcaster_subscriptions(
            self,
            limit: int,
            broadcaster_id: str = None,
            user_id: Union[Iterable[str], str] = None
    ) -> dict:
        """
        |Async Generator|\n
        Yields broadcaster’s subscriptions.\n
        REQUIRED scope: 'channel:read:subscriptions'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: `str`
                User ID of the broadcaster. Must match the User ID in the Bearer token.

            user_id: Union[`str`, Optional[`str`]]
                Returns broadcaster’s subscribers.
                Unique identifier of account to get subscription status of. Accepts up to 100 values.

        Yields:
        ================
            `dict` {
                'broadcaster_id': `str`
                    User ID of the broadcaster.

                'broadcaster_name': `str`
                   Display name of the broadcaster.

                'is_gift': `bool`
                    Determines if the subscription is a gift subscription.

                'tier': `int`
                    Type of subscription (Tier 1, Tier 2, Tier 3).
                    1000 = Tier 1, 2000 = Tier 2, 3000 = Tier 3 subscriptions.

                'plan_name': `str`
                    Name of the subscription.

                'user_id': `str`
                    ID of the subscribed user.

                'user_name': `str`
                    Display name of the subscribed user.
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        async for subscription in self.do_paginated_request_by_name('get_broadcaster_subscriptions', locals(), limit):
            yield subscription

    async def check_user_subscription(
            self,
            broadcaster_id: str,
            user_id: str,
    ) -> bool:
        try:
            await self.do_single_request_by_name('check_user_subscription', locals())
            return True
        # if HTTPError
        except HTTPError as error:
            response: ClientResponse = error.args[0]
            if response.status == 404:
                return False
            else:
                raise

    async def get_all_stream_tags(
            self,
            limit: int,
            tag_id: Union[Iterable[str], str] = None
    ) -> dict:
        """
        |Async Generator|\n
        Yields stream tags defined by Twitch, optionally filtered by tag ID(s).\n
        No REQUIRED scope

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            tag_id: `str`
                ID of a tag. Multiple IDs can be specified, separated by ampersands.
                If provided, only the specified tag(s) is(are) returned.

        Yields:
        ================
            `dict` {
                'tag_id': `str`
                    ID of the tag.

                'is_auto': `bool`
                    true if the tag is auto-generated; otherwise, false .
                    An auto-generated tag is one automatically applied by Twitch
                    (e.g., a language tag based on the broadcaster’s settings);
                    these tags cannot be added or removed by the user.

                'localization_names': `dict` {
                    '<some_localization>': `str`
                        name for the localization

                    Example:
                        'en-us': '1 Credit Clear'
                }

                'localization_descriptions': `dict` {
                    '<some_localization>': `str`
                        description for the localization
                }
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for tag in self.do_paginated_request_by_name('get_all_stream_tags', locals(), limit):
            yield tag

    async def get_stream_tags(
            self,
            limit: int,
            broadcaster_id: str
    ) -> dict:
        """
        |Async Generator|\n
        Yields  tags for a specified stream (channel).\n
        No REQUIRED scope

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: `str`
                ID of the stream thats tags are going to be fetched

        Yields:
        ================
            `dict` {
                'tag_id': `str`
                    ID of the tag.

                'is_auto': `bool`
                    true if the tag is auto-generated; otherwise, false .
                    An auto-generated tag is one automatically applied by Twitch
                    (e.g., a language tag based on the broadcaster’s settings);
                    these tags cannot be added or removed by the user.

                'localization_names': `dict` {
                    '<some_localization>': `str`
                        name for the localization

                    Example:
                        'en-us': '1 Credit Clear'
                }

                'localization_descriptions': `dict` {
                    '<some_localization>': `str`
                        description for the localization
                }
            }

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        async for tag in self.do_paginated_request_by_name('get_stream_tags', locals(), limit):
            yield tag

    async def replace_stream_tags(
            self,
            broadcaster_id: str = None,
            tag_ids: Iterable[str] = None
    ) -> None:
        """
        |Coroutine|\n
        Applies specified tags to a specified stream, overwriting any existing tags applied to that stream.
        If no tags are specified, all tags previously applied to the stream are removed.
        Automated tags are not affected by this operation.\n
        Tags expire 72 hours after they are applied, unless the stream is live within that time period.
        If the stream is live within the 72-hour window, the 72-hour clock restarts when the stream goes offline.
        The expiration period is subject to change.\n
        REQUIRED scope: 'user:edit:broadcast'

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            tag_id: Union[`str`, Iterable[`str`]]
                IDs of tags to be applied to the stream.
                Maximum of 100 supported.

        Returns:
        ================
            None:
                successfully modified

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        return await self.do_single_request_by_name('replace_stream_tags', locals())

    async def get_channel_teams(
            self,
            limit: int,
            broadcaster_id: str,
    ):
        async for team in self.do_paginated_request_by_name('get_channel_teams', locals(), limit):
            yield team

    async def get_teams(
            self,
            limit: int,
            name: str,
            team_id: str,
    ):
        id = team_id
        async for team in self.do_paginated_request_by_name('get_teams', locals(), limit):
            yield team

    async def get_users(
            self,
            limit: int,
            user_id: str = None,
            login: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|

        Yields  information about one or more specified Twitch users.
        Users are identified by optional user IDs and/or login name.
        If neither a user ID nor a login name is specified, the user is looked up by Bearer token.\n
        No REQUIRED scope ('user:read:email' to include the user’s email address in response.)

        Args:
            limit: `int`
                limit on number of returned values, 0 - unlimited

            user_id: `int`
                User ID. Multiple user IDs can be specified. Limit: 100.

            login: `str`
                User login name. Multiple login names can be specified. Limit: 100.

        Notes:
            Note: The limit of 100 IDs and login names is the total limit. You can request,
            for example, 50 of each or 100 of one of them. You cannot request 100 of both.

        Yields:
        ================
            `dict` {
                'id': `str`
                    User’s ID.

                'login': `str`
                    User’s login name.

                'display_name': `str`
                    User’s display name.

                'type': `str`
                    User’s type: "staff", "admin", "global_mod", or "".

                'broadcaster_type': `str`
                    User’s broadcaster type: "partner", "affiliate", or "".

                'description': `str`
                    User’s channel description.

                'profile_image_url': `str`
                    URL of the user’s profile image.

                'offline_image_url': `str`
                    URL of the user’s offline image.

                'view_count': `int`
                    Total number of views of the user’s channel.

                'email': `str`
                    User’s email address. Returned if the request includes the 'user:read:email' scope.

                'created_at': `str`
                    Date when the user was created.
            }

        Raises:
            `HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        """
        id = user_id
        async for user in self.do_paginated_request_by_name('get_users', locals(), limit):
            yield user

    async def update_user(
            self,
            description: str = None
    ) -> dict:
        """
        |Coroutine|
        Updates the description of a user specified by a Bearer token.\n
        REQUIRED scope: 'user:edit'

        Args:
            description: `str`
                User’s account description

        Returns:
            `dict` {
                'id': `str`
                    User’s ID.

                'login': `str`
                    User’s login name.

                'display_name': `str`
                    User’s display name.

                'type': `str`
                    User’s type: "staff", "admin", "global_mod", or "".

                'broadcaster_type': `str`
                    User’s broadcaster type: "partner", "affiliate", or "".

                'description': `str`
                    User’s channel description.

                'profile_image_url': `str`
                    URL of the user’s profile image.

                'offline_image_url': `str`
                    URL of the user’s offline image.

                'view_count': `int`
                    Total number of views of the user’s channel.

                'email': `str`
                    User’s email address. Returned if the request includes the 'user:read:email' scope.

                'created_at': `str`
                    Date when the user was created.
            }

        Raises:
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        """
        return await self.do_single_request_by_name('update_user', locals())

    async def get_users_follows(
            self,
            limit: int,
            from_id: str = None,
            to_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Yields Gets information on follow relationships between two Twitch users.
        This can return information like “who is qotrok following,” “who is following qotrok,”
        or “is user X following user Y.” Information yeilds is sorted in order, most recent follow first.\n
        No REQUIRED scope

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            from_id: `str`
                User ID. The request returns information about users who are being followed by the from_id user.

            to_id: `str`
                User ID. The request returns information about users who are following the to_id user.

            !Notes:
                Note: At minimum, `from_id` or `to_id` must be provided for a query to be valid.
        ----------------

        Yields:
        ================
            `dict` {
                'from_id': `str`
                    ID of the user following the to_id user.

                'from_name': `str`
                    Display name corresponding to from_id.

                'to_id': `str`
                    ID of the user being followed by the from_id user.

                'to_name': `str`
                    User’s type: "staff", "admin", "global_mod", or "".

                'followed_at': `str`
                    Display name corresponding to to_id.
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.
        ----------------
        """
        async for follow in self.do_paginated_request_by_name('get_users_follows', locals(), limit):
            yield follow

    async def create_user_follows(
            self,
            from_id: str,
            to_id: str,
            allow_notifications: bool = None
    ) -> dict:
        """
        |Coroutine|
        ================
        Adds a specified user to the followers of a specified channel.\n
        REQUIRED scope: 'user:edit:follows'

        ----------------

        Args:
        ================
            from_id: REQUIRED `str`
                User ID of the follower

            to_id: REQUIRED `str`
                ID of the channel to be followed by the user

            allow_notifications: `bool`
                If true, the user gets email or push notifications (depending on the user’s notification settings)
                when the channel goes live. Default value is false.
        ----------------

        Returns:
        ================
            None
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        return await self.do_single_request_by_name('create_user_follows', locals())

    async def delete_user_follows(
            self,
            from_id: str,
            to_id: str
    ) -> dict:
        """
        |Coroutine|
        ================
        Adds a specified user to the followers of a specified channel.\n
        REQUIRED scope: 'user:edit:follows'

        ----------------

        Args:
        ================
            from_id: REQUIRED `str`
                User ID of the follower

            to_id: REQUIRED `str`
                ID of the channel to be followed by the user
        ----------------

        Returns:
        ================
            None
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        return await self.do_single_request_by_name('delete_user_follows', locals())

    async def get_user_block_list(
            self,
            limit: int,
            broadcaster_id: int
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Yields a specified user’s block list. The list is sorted by when the block occurred in descending order
        (i.e. most recent block first).\n
        REQUIRED scope: 'user:read:blocked_users'

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            broadcaster_id: REQUIRED `str`
                User ID for a Twitch user.
        ----------------

        Yields:
        ================
            `dict` {
                'user_id': `str`
                    User ID of the blocked user.

                'user_login': `str`
                    Login of the blocked user.

                'display_name': `str`
                    Display name of the blocked user.
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        async for block in self.do_paginated_request_by_name('get_user_block_list', locals(), limit):
            yield block

    async def block_user(
            self,
            target_user_id: str,
            source_context: str,
            reason: str
    ) -> dict:
        """
        |Coroutine|
        ================
        Blocks the specified user on behalf of the authenticated user.\n
        REQUIRED scope: 'user:manage:blocked_users'

        ----------------

        Args:
        ================
            target_user_id: REQUIRED `str`
                User ID of the user to be blocked.

            source_context: `str`
                Source context for blocking the user. Valid values: "chat", "whisper".

            reason: `str`
                Reason for blocking the user. Valid values: "spam", "harassment", or "other".
        ----------------

        Returns:
        ================
            None
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        return await self.do_single_request_by_name('block_user', locals())

    async def unblock_user(
            self,
            target_user_id: str
    ) -> dict:
        """
        |Coroutine|
        ================
        Unblocks the specified user on behalf of the authenticated user.\n
        REQUIRED scope: 'user:manage:blocked_users'

        ----------------

        Args:
        ================
            target_user_id: REQUIRED `str`
                User ID of the user to be blocked.
        ----------------

        Returns:
        ================
            None
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        return await self.do_single_request_by_name('unblock_user', locals())

    async def get_user_extensions(
            self,
            limit: int,
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Yields  all extensions (both active and inactive) for a specified user, identified by a Bearer token.\n
        REQUIRED scope: 'user:read:broadcast'

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited
        ----------------

        Yields:
        ================
            `dict` {
                'can_activate': `bool`
                    Indicates whether the extension is configured such that it can be activated.

                'id': `str`
                    ID of the extension.

                'name': `str`
                    Name of the extension.

                'version': `str`
                    Version of the extension.

                'type': `list` [...]
                    Types for which the extension can be activated.
                    Valid values: "component", "mobile", "panel", "overlay".
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        async for extension in self.do_paginated_request_by_name('get_user_extensions', locals(), limit):
            yield extension

    async def get_user_active_extensions(
            self,
            limit: int,
            user_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        |Async Generator|
        ================
        Yields  all extensions (both active and inactive) for a specified user, identified by a Bearer token.\n
        REQUIRED scope: 'user:read:broadcast' or 'user:edit:broadcast'

        ----------------

        Args:
        ================
            limit: `int`
                limit on number of returned values, 0 - unlimited

            user_id: `str`
                ID of the user whose installed extensions will be returned. Limit: 1.
        ----------------

        Yields:
        ================
            `dict` {
                'can_activate': `bool`
                    Indicates whether the extension is configured such that it can be activated.

                'id': `str`
                    ID of the extension.

                'name': `str`
                    Name of the extension.

                'version': `str`
                    Version of the extension.

                'type': `list` [...]
                    Types for which the extension can be activated.
                    Valid values: "component", "mobile", "panel", "overlay".
            }
        ----------------

        Raises:
        ================
            :class:`HTTPError`:
                if status-code is not 2XX, passes `dict` with json of response.

            :class:`AccessError`:
                if the Authorization-Token hasn't required scope
        ----------------
        """
        async for extension in self.do_paginated_request_by_name('get_user_active_extensions', locals(), limit):
            yield extension

    async def update_user_extensions(
            self,
            new_extensions: dict,
    ):
        data = new_extensions
        return await self.do_single_request_by_name('update_user_extensions', locals())

    async def get_videos(
            self,
            limit: int,
            video_id: str = None,
            user_id: str = None,
            game_id: str = None,
            language: str = None,
            period: str = None,
            sort: str = None,
            type: str = None,
    ):
        id = video_id
        async for video in self.do_paginated_request_by_name('get_videos', locals(), limit):
            yield video

    async def delete_videos(
            self,
            video_id: str,
    ):
        id = video_id
        return await self.do_single_request_by_name('delete_videos', locals())

    async def get_webhook_subscriptions(
            self,
            limit: int
    ):
        async for subscription in self.do_paginated_request_by_name('get_webhook_subscriptions', locals(), limit):
            yield subscription

    @staticmethod
    def _get_stream_markers_json_preparer(json: Dict[str, Any]):
        for user in json['data']:
            for video in user['videos']:
                for marker in video['markers']:
                    marker: dict
                    marker.update(
                        {
                            'video_id': video['video_id'],
                            'user_id': user['user_id'],
                            'user_name': user['user_name'],
                            'user_login': user['user_login'],
                        }
                    )
                    yield marker

    @staticmethod
    def _get_user_active_extensions_json_preparer(json: Dict[str, Any]) -> List[dict]:
        data: Dict[str, Dict[str, Dict[str, Any]]] = json['data']
        for extension_type in data:
            for extension_number in data[extension_type]:
                extension = data[extension_type][extension_number]
                extension['type'] = extension_type
                extension['number'] = extension_number
                yield extension

    single_requests: Dict[str, SingleRequest] = {
        'start_commercial': SingleRequest(
            sub_url='/channels/commercial',
            http_method=_http_post,
            data_params_keys=('broadcaster_id', 'length'),
            scope='channel:edit:commercial'
        ),
        'modify_channel_information': SingleRequest(
            sub_url='/channels',
            http_method=_http_patch,
            data_params_keys=('game_id', 'title', 'broadcaster_language'),
            query_params_keys=('broadcaster_id', ),
            scope='channel:manage:broadcast'
        ),
        'create_custom_rewards': SingleRequest(
            sub_url='/channel_points/custom_rewards',
            http_method=_http_post,
            data_params_keys=('title',
                              'prompt',
                              'cost',
                              'is_enabled',
                              'background_color',
                              'is_user_input_required',
                              'is_max_per_stream_enabled',
                              'max_per_stream',
                              'is_max_per_user_per_stream_enabled',
                              'max_per_user_per_stream',
                              'is_global_cooldown_enabled',
                              'global_cooldown_seconds',
                              'should_redemptions_skip_request_queue'),
            query_params_keys=('broadcaster_id',),
            scope='channel:manage:redemptions'
        ),
        'delete_custom_reward': SingleRequest(
            sub_url='/channel_points/custom_rewards',
            http_method=_http_delete,
            query_params_keys=('broadcaster_id', 'id'),
            scope='channel:manage:redemptions'
        ),
        'update_custom_reward': SingleRequest(
            sub_url='/channel_points/custom_rewards',
            http_method=_http_patch,
            data_params_keys=('title',
                              'prompt',
                              'cost',
                              'is_enabled',
                              'background_color',
                              'is_user_input_required',
                              'is_max_per_stream_enabled',
                              'max_per_stream',
                              'is_max_per_user_per_stream_enabled',
                              'max_per_user_per_stream',
                              'is_global_cooldown_enabled',
                              'global_cooldown_seconds',
                              'is_paused',
                              'should_redemptions_skip_request_queue'),
            query_params_keys=('broadcaster_id', 'id'),
            scope='channel:manage:redemptions'
        ),
        'update_redemption_status': SingleRequest(
            sub_url='/channel_points/custom_rewards/redemptions',
            http_method=_http_patch,
            data_params_keys=('status',),
            query_params_keys=('broadcaster_id', 'reward_id', 'id'),
            scope='channel:manage:redemptions'
        ),
        'create_clip': SingleRequest(
            sub_url='/clips',
            http_method=_http_post,
            query_params_keys=('broadcaster_id', 'has_delay'),
            scope='clips:edit'
        ),
        'redeem_code': SingleRequest(
            sub_url='/entitlements/codes',
            http_method=_http_post,
            query_params_keys=('code', 'user_id'),
        ),
        'create_eventsub_subscription': SingleRequest(
            sub_url='/eventsub/subscriptions',
            http_method=_http_post,
            data_params_keys=('type', 'version', 'condition', 'transport'),
        ),
        'delete_eventsub_subscription': SingleRequest(
            sub_url='/eventsub/subscriptions',
            http_method=_http_delete,
            query_params_keys=('id',),
        ),
        'check_automod_status': SingleRequest(
            sub_url='/moderation/enforcements/status',
            http_method=_http_post,
            data_params_keys=('data',),
            query_params_keys=('broadcaster_id',),
        ),
        'create_stream_marker': SingleRequest(
            sub_url='/streams/markers',
            http_method=_http_post,
            data_params_keys=('user_id', 'description'),
            scope='channel:manage:broadcast'
        ),
        'check_user_subscription': SingleRequest(
            sub_url='/subscriptions/user',
            http_method=_http_get,
            query_params_keys=('broadcaster_id', 'user_id'),
            scope='user:read:subscriptions'
        ),
        'replace_stream_tags': SingleRequest(
            sub_url='/streams/tags',
            http_method=_http_put,
            data_params_keys=('tag_ids',),
            query_params_keys=('broadcaster_id',),
            scope='channel:manage:broadcast'
        ),
        'update_user': SingleRequest(
            sub_url='/users',
            http_method=_http_put,
            query_params_keys=('description',),
            scope='user:edit'
        ),
        'create_user_follows': SingleRequest(
            sub_url='/users/follows ',
            http_method=_http_post,
            query_params_keys=('from_id', 'to_id', 'allow_notifications'),
            scope='user:edit:follows'
        ),
        'delete_user_follows': SingleRequest(
            sub_url='users/follows',
            http_method=_http_delete,
            query_params_keys=('from_id', 'to_id'),
            scope='user:edit:follows'
        ),
        'block_user': SingleRequest(
            sub_url='/users/blocks',
            http_method=_http_put,
            query_params_keys=('target_user_id', 'source_context', 'reason'),
            scope='user:manage:blocked_users'
        ),
        'unblock_user': SingleRequest(
            sub_url='/users/blocks',
            http_method=_http_delete,
            query_params_keys=('target_user_id',),
            scope='user:manage:blocked_users'
        ),
        'update_user_extensions': SingleRequest(
            sub_url='/users/extensions',
            http_method=_http_put,
            data_params_keys=('data',),
            scope='user:edit:broadcast'
        ),
        'delete_videos': SingleRequest(
            sub_url='/videos',
            http_method=_http_delete,
            query_params_keys=('id',),
            scope='channel:manage:videos'
        )
    }

    paginated_requests: Dict[str, PaginatedRequest] = {
        'get_extension_analytics': PaginatedRequest(
            sub_url='/analytics/extensions',
            max_first=100,
            query_params_keys=('first', 'extension_id', 'started_at', 'ended_at', 'type'),
            scope='analytics:read:extensions'
        ),
        'get_game_analytics': PaginatedRequest(
            sub_url='/analytics/games',
            max_first=100,
            query_params_keys=('first', 'game_id', 'started_at', 'ended_at', 'type'),
            scope='analytics:read:games'
        ),
        'get_bits_leaderboard': PaginatedRequest(
            sub_url='/bits/leaderboard',
            max_first=100,
            query_params_keys=('count', 'user_id', 'started_at', 'period'),
            scope='bits:read'
        ),
        'get_cheermotes': PaginatedRequest(
            sub_url='/bits/cheermotes',
            query_params_keys=('broadcaster_id',)
        ),
        'get_extension_transactions': PaginatedRequest(
            sub_url='/extensions/transactions',
            max_first=100,
            query_params_keys=('first', 'extension_id', 'id'),
        ),
        'get_channel_information': PaginatedRequest(
            sub_url='/channels',
            query_params_keys=('broadcaster_id',),
        ),
        'get_channel_editors': PaginatedRequest(
            sub_url='/channels/editors',
            query_params_keys=('broadcaster_id',),
            scope='channel:read:editors'
        ),
        'get_custom_reward': PaginatedRequest(
            sub_url='/channel_points/custom_rewards',
            query_params_keys=('broadcaster_id', 'id', 'only_manageable_rewards'),
            scope='channel:read:redemptions'
        ),
        'get_custom_reward_redemption': PaginatedRequest(
            sub_url='/channel_points/custom_rewards/redemptions',
            max_first=50,
            query_params_keys=('broadcaster_id', 'reward_id', 'id', 'status', 'sort'),
            scope='channel:read:redemptions'
        ),
        'get_clips': PaginatedRequest(
            sub_url='/clips',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id', 'game_id', 'id', 'started_at', 'ended_at'),
        ),
        'get_code_status': PaginatedRequest(
            sub_url='/entitlements/codes',
            query_params_keys=('code', 'user_id'),
        ),
        'get_drops_entitlements': PaginatedRequest(
            sub_url='/entitlements/drops',
            max_first=1000,
            query_params_keys=('first', 'id', 'user_id', 'game_id'),
        ),
        'get_top_games': PaginatedRequest(
            sub_url='/games/top',
            max_first=100,
            query_params_keys=('first',),
        ),
        'get_games': PaginatedRequest(
            sub_url='/games',
            max_first=100,
            query_params_keys=('id', 'name'),
        ),
        'get_eventsub_subscriptions': PaginatedRequest(
            sub_url='eventsub/subscriptions',
            query_params_keys=('status', 'type'),
        ),
        'get_hype_train_events': PaginatedRequest(
            sub_url='/hypetrain/events',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id', 'id'),
            scope='channel:read:hype_train'
        ),
        'get_banned_events': PaginatedRequest(
            sub_url='/moderation/banned/events',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id'),
            scope='moderation:read'
        ),
        'get_banned_users': PaginatedRequest(
            sub_url='/moderation/banned',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id', 'user_id'),
            scope='moderation:read'
        ),
        'get_moderators': PaginatedRequest(
            sub_url='/moderation/moderators',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id', 'user_id'),
            scope='moderation:read'
        ),
        'get_moderator_events': PaginatedRequest(
            sub_url='/moderation/moderators/events',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id', 'user_id'),
            scope='moderation:read'
        ),
        'search_categories': PaginatedRequest(
            sub_url='/search/categories',
            max_first=100,
            query_params_keys=('first', 'query')
        ),
        'search_channels': PaginatedRequest(
            sub_url='/search/channels',
            max_first=100,
            query_params_keys=('first', 'query', 'live_only'),
        ),
        'get_stream_key': PaginatedRequest(
            sub_url='/streams/key',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id'),
            scope='channel:read:stream_key'
        ),
        'get_streams': PaginatedRequest(
            sub_url='/streams',
            max_first=100,
            query_params_keys=('first', 'game_id', 'language', 'user_id', 'user_login')
        ),
        'get_stream_markers': PaginatedRequest(
            sub_url='/streams/markers',
            max_first=100,
            query_params_keys=('first', 'user_id', 'video_id'),
            scope='user:read:broadcast',
            response_json_preparer=_get_stream_markers_json_preparer
        ),
        'get_broadcaster_subscriptions': PaginatedRequest(
            sub_url='/subscriptions',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id', 'user_id'),
            scope='channel:read:subscriptions'
        ),
        'get_all_stream_tags': PaginatedRequest(
            sub_url='/tags/streams',
            max_first=100,
            query_params_keys=('first', 'tag_id'),
        ),
        'get_stream_tags': PaginatedRequest(
            sub_url='/tags/streams',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id'),
        ),
        'get_channel_teams': PaginatedRequest(
            sub_url='/teams/channel',
            query_params_keys=('broadcaster_id',),
        ),
        'get_teams': PaginatedRequest(
            sub_url='/teams',
            query_params_keys=('name', 'id'),
        ),
        'get_users': PaginatedRequest(
            sub_url='/users',
            query_params_keys=('id', 'login'),
            scope='user:read:email'
        ),
        'get_users_follows': PaginatedRequest(
            sub_url='/users/follows',
            max_first=100,
            query_params_keys=('first', 'from_id', 'to_id'),
        ),
        'get_user_block_list': PaginatedRequest(
            sub_url='/users/blocks',
            max_first=100,
            query_params_keys=('first', 'broadcaster_id'),
            scope='user:read:blocked_users'
        ),
        'get_user_extensions': PaginatedRequest(
            sub_url='/users/extensions/list',
            scope='user:read:broadcast'
        ),
        'get_user_active_extensions': PaginatedRequest(
            sub_url='/users/extensions',
            max_first=100,
            query_params_keys=('user_id',),
            # scope='user:read:broadcast' or 'user:edit:broadcast'
            response_json_preparer=_get_user_active_extensions_json_preparer
        ),
        'get_videos': PaginatedRequest(
            sub_url='/videos',
            max_first=100,
            query_params_keys=('first', 'id', 'user_id', 'game_id', 'language', 'period', 'sort', 'type'),
        ),
        'get_webhook_subscriptions': PaginatedRequest(
            sub_url='/webhooks/subscriptions',
            max_first=100,
        )
    }
