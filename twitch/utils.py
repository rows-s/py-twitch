import hmac
from datetime import datetime
from hashlib import sha256

from typing import Iterable


__all__ = (
    'calc_sha256',
    'str_to_datetime',
    'normalize_ms',
    'remove_not_valid_postfix'
)


def calc_sha256(
        text: str,
        key: str,
) -> str:
    """
    Calculates sha256 hash of `text` with `key`

    Args:
        text: `str`
            text to hash
        key: `str`
            key to hash

    Returns:
            calculated sha256 hash (str)
    """
    text_bytes = bytes(text, 'utf-8')
    key_bytes = bytes(key, 'utf-8')
    signature = hmac.new(key_bytes, text_bytes, sha256).hexdigest()
    return signature


def str_to_datetime(
        datetime_str: str,
        should_normalize_ms: bool = True
) -> datetime:
    if should_normalize_ms:
        datetime_str = normalize_ms(datetime_str)
    return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f')


def normalize_ms(
        datetime_str: str,
        valid_symbols: Iterable[str] = '-:.0123456789',
        max_ms_len: int = 6
) -> str:
    datetime_str = remove_not_valid_postfix(datetime_str, valid_symbols)
    dot_index = datetime_str.find('.')
    # if not contains a dot
    if dot_index == -1:
        datetime_str = datetime_str + '.0'
    # if contains a dot
    else:
        ms_len = len(datetime_str) - (dot_index + 1)
        # if greater than max len
        if ms_len > max_ms_len:
            datetime_str = datetime_str[:dot_index + max_ms_len + 1]  # length of ms must not be more than 6 symbols
        # if has no ms
        elif ms_len == 0:
            datetime_str += '0'
    return datetime_str


def remove_not_valid_postfix(
        string: str,
        valid_symbols: Iterable[str] = None,
        invalid_symbols: Iterable[str] = None
):
    """
    Removes not valid postfix. Removes all symbols from the end that are not in `valid_symbols`
    or are in `invalid_symbols`. Only one of `valid_symbols` or `invalid_symbols` must be specified.

    Args:
        string: str
            string from which postfix must be removed
        valid_symbols: Iterable[str] (Default: None)
            Use if you want to specify small number of valid symbols
            if specified would work as "delete everything except these symbols"
        invalid_symbols: Iterable[str] (Default: None)
            Use if you want to specify small number of invalid symbols
            if specified would work as "delete only these symbols"

    Returns:
        string without postfix
    """
    if valid_symbols is None and invalid_symbols is None:
        raise TypeError('None of valid_symbols` and `invalid_symbols` is specified')
    elif valid_symbols is not None and invalid_symbols is not None:
        raise TypeError('Only one of `valid_symbols` and `invalid_symbols` must be specified')

    index = len(string)

    if valid_symbols is not None:
        for symbol in reversed(string):
            if symbol in valid_symbols:
                break
            else:
                index -= 1
    elif invalid_symbols is not None:
        for symbol in reversed(string):
            if symbol not in invalid_symbols:
                break
            else:
                index -= 1
    return string[:index]
