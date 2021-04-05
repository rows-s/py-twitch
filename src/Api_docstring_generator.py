from typing import NamedTuple, Iterable, Optional, Any, Type, List, Union, Dict
from textwrap import wrap
from copy import copy


def prepare_type(the_type: Any):
    if str(the_type).startswith('<class'):
        the_type: str = the_type.__name__  # name of the class
    else:
        the_type: str = str(the_type).replace('typing.', '')  # delete prefixes if exists\
    return the_type


def prepare_to_show(the_object: Any):
    if type(the_object) == str:
        the_object: str
        if the_object.startswith('^'):
            return the_object[1:]
        else:
            return f"'{the_object}'"
    else:
        return str(the_object)


class Arg:
    def __init__(
            self,
            name: str,
            the_type: Type,
            description: str,
            required: bool = False,
            multiple: bool = False,
            valid_values: Optional[List[Any]] = None,
            default: Optional[Any] = None
    ) -> None:
        self.name: str = name
        self.type: Type = the_type
        self.description: str = description
        self.required: bool = required
        self.multiple: bool = multiple
        self.valid_values: List = valid_values
        self.default = default
        # default

    def __repr__(self):
        # type
        the_type = prepare_type(self.type)
        # required
        if self.required:
            required: str = 'REQUIRED;'
        else:
            required = ''
        # multiple
        if self.multiple:
            multiple: str = 'MULTIPLE;'
        else:
            multiple = ''
        # valid_values
        if self.valid_values is not None:
            valid_values = list(map(prepare_to_show, self.valid_values))
            valid_values = 'VALID VALUES: ' + ' '.join(valid_values) + ';'  # join with spaces if exists
        else:
            valid_values = ''
        # default
        if self.default is not None:
            default = prepare_to_show(self.default)
            default: str = 'DEFAULT: ' + default + ';'
        else:
            default: str = ''
        # whole_description
        if any([required, multiple, valid_values, default]):
            description_sep = '\n' + ' ' * 19
            description = description_sep.join(wrap(self.description, 101))
            whole_description = f'''1. {required} {multiple} {valid_values} {default}
                2. {description}'''
        else:
            description_sep = '\n' + ' ' * 16
            description = description_sep.join(wrap(self.description, 104))
            whole_description = f'{description}'
        # description

        return f"""{self.name}: `{the_type}`
                {whole_description}"""


class Return:
    def __init__(
            self,
            return_object: Any
    ) -> None:
        self.return_object: Any = return_object

    def __repr__(self):
        sub_types = [dict, list]

        def call_maker(the_object: Union[dict, list], spaces_before) -> str:
            if type(the_object) == dict:
                return make_dict_based_str('', the_object, spaces_before)
            else:
                return make_list_based_str('', the_object, spaces_before)

        def make_list_based_str(
                string,
                the_object: Any,
                spaces_before: int = 16
        ) -> str:
            pass

        def make_dict_based_str(
                string,
                the_object: Any,
                spaces_before: int = 16
        ) -> str:
            string += '{'
            newline_indent = '\n' + ' ' * spaces_before
            add_indent = ' '*4
            for key in the_object:
                # key
                string += f"{newline_indent}'{key}': "
                # value
                value = the_object[key][0]
                # sub object
                if type(value) in sub_types:
                    string += call_maker(value, spaces_before + 4)
                # type
                else:
                    the_type = prepare_type(value)
                    string += f"`{the_type}`"
                # description
                description = the_object[key][1]
                if string[-1] == '}':
                    description_indent = newline_indent + add_indent[:-1]
                    description_parts = wrap(description, 120-(spaces_before+4))
                    string += ', ' + description_indent.join(description_parts)
                    if len(description_parts) == 1:
                        string += '\n'
                else:
                    description_indent = newline_indent + add_indent
                    string += description_indent
                    string += description_indent.join(wrap(description, 120-(spaces_before+4)))
            return string + newline_indent[:-4] + '}'
        # main code branch
        return call_maker(self.return_object, spaces_before=16)
Yield = Return


class Raise:
    def __init__(
            self,
            name: str,
            description: str
    ) -> None:
        self.name: str = name
        self.description: str = description

    def __repr__(self):
        newline_indent = '\n' + ' '*16
        description = newline_indent.join(wrap(self.description, 104))
        return f"""{self.name}:
                {description}"""


class Doc:
    def __init__(
            self,
            description: str,
            scope: str,
            access: str,
            args: Iterable[Arg],
            returns: Any = None,
            yields: Any = None,
            raises: Optional[Iterable[Raise]] = None,
    ) -> None:
        self.description: str = description
        self.scope: str = scope
        self.access: str = access
        self.args: Iterable[Arg] = args
        self.returns: Return = returns
        self.yields: Return = yields
        self.raises: Optional[Iterable[Raise]] = raises
        if returns is not None:
            self.type = 'Coroutine'
            self.does = 'Returns'
        else:
            self.type = 'AsyncGenerator'
            self.does = 'Yields'

    def __repr__(self):
        hilight = '----------'
        newline = '\n'
        newline_indent = newline + ' '*12
        return f"""
        |{self.type}|

        {newline_indent[:-4].join(wrap(self.description, 112))}

        1. SCOPE: '{self.scope}'
        2. ACCESS: {newline_indent[:-4].join(wrap(self.access, 112))}

        Args:
        {hilight}
            {newline_indent.join([str(the_arg) for the_arg in self.args])}

        {self.does}:
        {hilight}
            dict: {self.returns if (self.returns is not None) else self.yields}
        
        Raises:
            {newline_indent.join([str(the_raise) for the_raise in self.raises])}
        """


limit_arg = Arg('limit', int, required=True, description='limit on number of yields, 0 - unlimited')
HTTPError = Raise('HTTPError', description='if status-code of response is not 2XX. passes response.')
AccessError = Raise('AccessError', description='if the Token has not required scope. passes response.')

to_print: Dict[str, Doc] = dict()

to_print['create_app_token'] = Doc(
    description='creates an app `token`',
    scope='',
    access='',
    args=[
        Arg('client_id', str,
            description='Your client ID'),
        Arg('client_secret', str,
            description='Your client secret'),
        Arg('grant_type', str,
            description="not described", valid_values=['client_credentials'], default='client_credentials'),
        Arg('scope', str,
            description='Space-separated list of scopes')
    ],
    returns=Return({
        'access_token':
            (str, 'user access token'),
        'refresh_token':
            (str, 'not described'),
        'expires_in':
            (str, 'number of seconds until the token expires'),
        'scope':
            (str, 'your previously listed scope(s)'),
        'token_type':
            (str, 'bearer'),
    }),
    raises=[HTTPError]
)

to_print['start_commercial'] = Doc(
    description='Starts a commercial on a specified channel.',
    scope='channel:edit:commercial',
    access='OAuth Token required',
    args=[
        Arg('broadcaster_id', str, required=True,
            description='ID of the channel requesting a commercial. Minimum: 1 Maximum: 1'),
        Arg('length', int, required=True, valid_values=[30, 60, 90, 120, 150, 180],
            description='Desired length of the commercial in seconds.')
    ],
    returns=Return({
        'length':
            (int, 'Length of the triggered commercial'),
        'message':
            (str, 'Provides contextual information on why the request failed'),
        'retry_after':
            (int, 'Seconds until the next commercial can be served on this channel'),
    }),
    raises=[HTTPError, AccessError]
)

to_print['get_extension_analytics'] = Doc(
    description='Gets a URL that Extension developers can use to download analytics reports (CSV files) '
                'for their Extensions. The URL is valid for 5 minutes.'  
                '\nNote: If you specify a future date, the response will be "Report Not Found For Date Range." '
                'If you leave both `started_at` and `ended_at` blank, the API returns the most recent date of data.',
    scope='analytics:read:extensions',
    access='OAuth token required',
    args=[
        limit_arg,
        Arg('extension_id', str,
            description='Client ID value assigned to the extension when it is created.  If this is specified, '
                        'the returned URL points to an analytics report for just the specified extension. '
                        'If this is not specified, the response includes multiple URLs, '
                        'pointing to separate analytics reports for each of the authenticated user’s Extensions.'),
        Arg('started_at', str, valid_values=['^after January 31, 2018'], default='2018-01-31T00:00:00Z',
            description="Starting date/time for returned reports, in RFC3339 format "
                        "with the hours, minutes, and seconds zeroed out and the UTC timezone: 'YYYY-MM-DDT00:00:00Z'. "
                        "This must be on or after January 31, 2018. If this is provided, "
                        "`ended_at` also must be specified.  The file contains one row of data per day."),
        Arg('ended_at', str, default='^1-2 days before the request was issued',
            description="Ending date/time for returned reports, in RFC3339 format "
                        "with the hours, minutes, and seconds zeroed out and the UTC timezone: 'YYYY-MM-DDT00:00:00Z'. "
                        "The report covers the entire ending date; e.g., if '2018-05-01T00:00:00Z' is specified, "
                        "the report covers up to '2018-05-01T23:59:59Z'. "
                        "If this is provided, started_at also must be specified. "
                        "If ended_at is later than the default end date, the default date is used. "
                        "Default: 1-2 days before the request was issued (depending on report availability)."),
        Arg('type', str, default='overview_v2',
            description="Type of analytics report that is returned. "
                        "Currently, this field has no affect on the response as there is only one report type. "
                        "If additional types were added, using this field would return only the URL "
                        "for the specified report. Limit: 1. Valid values: 'overview_v2'.")
    ],
    yields=Yield({
        'extension_id':
            (str, 'ID of the extension whose analytics data is being provided.'),
        'URL':
            (str, 'URL to the downloadable CSV file containing analytics data. Valid for 5 minutes.'),
        'type':
            (str, 'Type of report.'),
        'date_range': ({
            'started_at':
                (str, 'Report start date/time. Note this may differ from (be later than) '
                      'the started_at value in the request; '
                      'the response value is the date when data for the extension is available.'),
            'ended_at':
                (str, 'Report end date/time.'),
        }, 'object contains data range parameters')
    }),
    raises=[HTTPError, AccessError]
)

to_print['get_game_analytics'] = Doc(
    description='Gets a URL that game developers can use to download analytics reports (CSV files) for their games. '
                'The URL is valid for 5 minutes. '
                'For detail about analytics and the fields returned, see the Insights & Analytics guide.'
                'Note: If you specify a future date, the response will be "Report Not Found For Date Range." '
                'If you leave both started_at and ended_at blank, the API returns the most recent date of data.',
    scope='analytics:read:games',
    access='OAuth token required',
    args=[
        Arg('game_id', str,
            description='Game ID. If this is specified, '
                        'the returned URL points to an analytics report for just the specified game. '
                        'If this is not specified, the response includes multiple URLs, '
                        'pointing to separate analytics reports for each of the authenticated user’s games.'),
        Arg('started_at', str, default='^365 days before the report was issued',
            description="Starting date/time for returned reports, in RFC3339 format "
                        "with the hours, minutes, and seconds zeroed out and the UTC timezone: 'YYYY-MM-DDT00:00:00Z'. "
                        "If this is provided,  `ended_at` also must be specified. "
                        "The file contains one row of data per day."),
        Arg('ended_at', str, default='^1-2 days before the request was issued',
            description="Ending date/time for returned reports, in RFC3339 format "
                        "with the hours, minutes, and seconds zeroed out and the UTC timezone: 'YYYY-MM-DDT00:00:00Z'. "
                        "The report covers the entire ending date; e.g., if '2018-05-01T00:00:00Z' is specified, "
                        "the report covers up to '2018-05-01T23:59:59Z'. "
                        "If this is provided, started_at also must be specified. "
                        "If ended_at is later than the default end date, the default date is used. "),
        Arg('type', str, default='overview_v2',
            description="Type of analytics report that is returned. "
                        "Currently, this field has no affect on the response as there is only one report type. "
                        "If additional types were added, using this field would return only the URL "
                        "for the specified report. Limit: 1. Valid values: 'overview_v2'.")
    ],
    yields=Yield({
        'game_id':
            (str, 'ID of the game whose analytics data is being provided.'),
        'URL':
            (str, 'URL to the downloadable CSV file containing analytics data. Valid for 5 minutes.'),
        'type':
            (str, 'Type of report.'),
        'date_range': ({
            'started_at':
                (str, 'Report start date/time. Note this may differ from (be later than) '
                      'the started_at value in the request; '
                      'the response value is the date when data for the extension is available.'),
            'ended_at':
                (str, 'Report end date/time.'),
        }, 'object contains data range parameters')
    }),
    raises=[HTTPError, AccessError]
)

to_print['get_bits_leaderboard'] = Doc(
    description='Gets a ranked list of Bits leaderboard information for an authorized broadcaster.',
    scope='bits:read',
    access='OAuth token required',
    args=[
        limit_arg,
        Arg('period', str, valid_values=['day', 'week', 'month', 'year', 'all'], default='all',
            description="Time period over which data is aggregated (PST time zone). "
                        "This parameter interacts with started_at. Valid values follow. Default: 'all'."
                        "Note: 'day', 'week', 'month', 'year' are equal to the entire day, week, month, year "
                        "from `started_at`"),
        Arg('started_at', str,
            description='Timestamp for the period over which the returned data is aggregated. '
                        'Must be in RFC 3339 format. '
                        'If this is not provided, data is aggregated over the current period; e.g., '
                        'the current day/week/month/year. This value is ignored if period is "all".'
                        'Any + operator should be URL encoded.'),
        Arg('user_id', str,
            description='ID of the user whose results are returned; i.e., the person who paid for the Bits.'
                        'As long as `limit` is greater than 1, the returned data includes additional users, '
                        'with Bits amounts above and below the user specified by `user_id`. '
                        'If `user_id` is not provided, the endpoint returns the Bits leaderboard data across top users '
                        '(subject to the value of `limit`).')
    ],
    returns=Return({
        'user_id':
            (str, 'ID of the user (viewer) in the leaderboard entry.'),
        'user_login':
            (str, 'User login name'),
        'user_name':
            (str, 'Display name corresponding to `user_id`.'),
        'rank':
            (int, 'Leaderboard rank of the user'),
        'score':
            (int, 'Leaderboard score (number of Bits) of the user.')
    }),
    raises=[HTTPError, AccessError]
)

to_print['update_custom_reward'] = Doc(
    description='Updates a Custom Reward created on a channel. '
                'Only rewards created programmatically by the same client_id can be updated.',
    scope='channel:manage:redemptions',
    access='Query parameter broadcaster_id must match the user_id in the User Access token'
           'The Custom Reward specified by id must have been created by the client_id attached to the access token.',
    args=[
        Arg('broadcaster_id', str, required=True,
            description='Provided broadcaster_id must match the user_id in the auth token.'*4),
        Arg('reward_id', str, required=True,
            description='ID of the Custom Reward to update, must match a Custom Reward on broadcaster_id’s channel.'),
        Arg('title', str,
            description='The title of the reward'),
        Arg('prompt', str,
            description='The prompt for the viewer when they are redeeming the reward'),
        Arg('cost', int,
            description='The cost of the reward'),
        Arg('background_color', str,
            description='Custom background color for the reward. Format: Hex with # prefix. Example: #00E5CB.'),
        Arg('is_enabled', bool,
            description='Is the reward currently enabled, if false the reward won’t show up to viewers'),
        Arg('is_user_input_required', bool,
            description='Does the user need to enter information when redeeming the reward.'),
        Arg('is_max_per_stream_enabled', bool,
            description='Whether a maximum per stream is enabled'),
        Arg('max_per_stream', int,
            description='The maximum number per stream if enabled'),
        Arg('is_max_per_user_per_stream_enabled', bool,
            description='Whether a maximum per user per stream is enabled'),
        Arg('max_per_user_per_stream', int,
            description='The maximum number per user per stream if enabled.'),
        Arg('is_global_cooldown_enabled', bool,
            description='Whether a cooldown is enabled.'),
        Arg('global_cooldown_seconds', int,
            description='The cooldown in seconds if enabled.'),
        Arg('is_paused', bool,
            description='Is the reward currently paused, if true viewers can’t redeem'),
        Arg('should_redemptions_skip_request_queue', bool,
            description='Should redemptions be set to FULFILLED status immediately when redeemed '
                        'and skip the request queue instead of the normal UNFULFILLED status.')
    ],
    returns=Return({
        'id':
            (str, 'ID of the reward'),
        'broadcaster_id':
            (str, 'ID of the channel the reward is for'),
        'broadcaster_login':
            (str, 'Broadcaster’s user login name.'),
        'broadcaster_name':
            (str, 'Display name of the channel the reward is for'),
        'title':
            (str, 'The title of the reward'),
        'cost':
            (int, 'The cost of the reward'),
        'prompt':
            (str, 'The prompt for the viewer when they are redeeming the reward'),
        'background_color':
            (str, 'Custom background color for the reward. Example: #00E5CB'),
        'is_paused':
            (bool, 'Is the reward currently paused, if true viewers can’t redeem'),
        'is_enabled':
            (bool, 'Is the reward currently enabled, if false the reward won’t show up to viewers'),
        'is_in_stock':
            (bool, 'Is the reward currently in stock, if false viewers can’t redeem'),
        'is_user_input_required':
            (bool, 'Does the user need to enter information when redeeming the reward'),
        'should_redemptions_skip_request_queue':
            (bool, 'Should redemptions be set to FULFILLED status immediately when redeemed '
                   'and skip the request queue instead of the normal UNFULFILLED status.'),
        'redemptions_redeemed_current_stream':
            (Optional[int], 'The number of redemptions redeemed during the current live stream. '
                            'Counts against the max_per_stream_setting limit. '
                            'Null if the broadcasters stream isn’t live or max_per_stream_setting isn’t enabled.'),
        'cooldown_expires_at':
            (Optional[str], 'Timestamp of the cooldown expiration. None if the reward isn’t on cooldown'),

        'max_per_stream_setting': ({
            'is_enabled':
                (bool, 'marks if this enabled'),
            'max_per_stream':
                (int, 'The maximum number per stream if enabled')
        }, 'Whether a maximum per stream is enabled and what the maximum is. '),

        'max_per_user_per_stream_setting': ({
            'is_enabled':
                (bool, 'marks if this enabled'),
            'max_per_user_per_stream':
                (int, 'The maximum number per user per stream if enabled, else - 0')
        }, 'Whether a maximum per user per stream is enabled and what the maximum is'),

        'global_cooldown_setting': ({
            'is_enabled':
                (bool, 'marks if this enabled'),
            'global_cooldown_seconds':
                (int, 'The cooldown in seconds if enabled, else - 0')
        }, 'Whether a cooldown is enabled and what the cooldown is.'),

        'image': ({
            'url_1x':
                (str, 'download url of 1x image'),
            'url_2x':
                (str, 'download url of 2x image'),
            'url_4x':
                (str, 'download url of 4x image')
        }, 'object contains download urls of custom images, can be None if no images have been uploaded'),

        'default_image': ({
            'url_1x':
                (str, 'download url of 1x image'),
            'url_2x':
                (str, 'download url of 2x image'),
            'url_4x':
                (str, 'download url of 4x image')
        }, 'object contains download urls of default images.'),
    }),
    raises=[HTTPError, AccessError]
)


if __name__ == '__main__':
    while True:
        to_output = input('Input type: ')
        if to_output == 'all':
            for name, body in to_print.items():
                print(name, body)
        else:
            print(to_print.get(to_output,
                               f'Not found: {to_output}'))
