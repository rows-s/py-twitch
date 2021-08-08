from dataclasses import InitVar, dataclass
from typing import Iterable, Dict, Any, Tuple, Callable, Optional


__all__ = (
    'BaseRequest',
    'SingleRequest',
    'PaginatedRequest'
)


@dataclass()
class BaseRequest:
    sub_url: InitVar[str]
    data_params_keys: Iterable[str] = ()
    query_params_keys: Iterable[str] = ()

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
        return super().distribute_raw_params(raw_params, *args, **kwargs)
