from typing import Dict, Tuple, List, Iterable
from .flags import Flag
from .emotes import Emote


__all__ = (
    'parse_raw_emotes',
    'is_emote_only',
    'parse_raw_flags',
    'parse_raw_badges',
    'escape_tag_value',
    'unescape_tag_value'
)


def parse_raw_emotes(
        raw_emotes: str,
        content: str
) -> Tuple[Emote]:
    emotes = []
    if raw_emotes:
        for emote in raw_emotes.split('/'):
            emote_id, raw_positions = emote.split(':', 1)
            positions = [_split_raw_position(raw_position) for raw_position in raw_positions.split(',')]
            start, end = positions[0]
            emotes.append(Emote(emote_id, content[start: end], positions))
    return tuple(emotes)


def _split_raw_position(raw_position: str):
    start, end = map(int, raw_position.split('-', 1))
    return start, end+1


def is_emote_only(
        content: str,
        emotes: Iterable[Emote]
) -> bool:
    if not content:
        return False
    emotes_count: int = 0
    emotes_length: int = 0
    for emote in emotes:
        emotes_count += emote.count
        emotes_length += emote.count * len(emote.content)
    # if length of all emotes + count of space between each emote equals all content -> is emotes only
    return emotes_length + (emotes_count - 1) == len(content)


def parse_raw_badges(
        badges: str
) -> Dict[str, str]:
    if not badges:
        return {}
    result = {}
    # for exampe: badges = 'predictions/KEENY DEYY,vip/1'
    for badge in badges.split(','):  # badge = 'predictions/KEENY DEYY'
        key, value = badge.split('/', 1)  # key = 'predictions', value = 'KEENY DEYY'
        result[key] = value  # result = {'predictions': 'KEENY DEYY'}
    return result  # result = {'predictions': 'KEENY DEYY', 'vip': '1'}


def parse_raw_flags(raw_flags: str, content: str) -> Tuple[Flag]:
    flags: List[Flag] = []
    if raw_flags:
        for raw_flag in raw_flags.split(','):
            raw_position, raw_flag_ids = raw_flag.split(':', 1)
            start, end = map(int, raw_position.split('-', 1))
            end += 1
            flags_ids = raw_flag_ids.split('/')
            flags.append(Flag(flags_ids, content[start:end], start, end))
    return tuple(flags)


def escape_tag_value(value: str):
    r"""
    Escapes value: ' ' -> '\s', ';' -> '\:', '\' -> '\\'.
    '\r' and '\n' (CR and LF) don't need to be escaped.
    """
    return value.replace('\\', '\\\\').replace(' ', r'\s').replace(';', r'\:')


def unescape_tag_value(value: str) -> str:
    r"""
    Unescapes escaped value: '\s' -> ' ', '\:' -> ';', '\\' -> '\'.
    '\r' and '\n' (CR and LF) don't need to be unescaped.
    """
    return value.replace(r'\:', ';').replace(r'\s', ' ').replace('\\\\', '\\')
