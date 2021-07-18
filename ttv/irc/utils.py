from typing import Dict, Tuple, List


__all__ = (
    'parse_raw_emotes',
    'is_emote_only',
    'parse_raw_badges',
    'unescape_tag_value'
)


def parse_raw_emotes(
        emotes: str
) -> Dict[str, List[Tuple[int, int]]]:
    if not emotes:
        return {}
    result = {}
    # for example: emotes = 'emote1:0-1,2-3,4-5,8-9/emote2:6-7'
    for emote in emotes.split('/'):  # emote = 'emote1:0-1,2-3,4-5,8-9'
        positions = []  # positions of current emote_id
        emote_id, raw_positions = emote.split(':', 1)  # emote_id = 'emote1', raw_positions = '0-1,2-3,4-5,8-9'
        for raw_position in raw_positions.split(','):  # raw_position = '0-1' from = ('0-1', '2-3', '4-5', '8-9')
            start, end = raw_position.split('-')  # start = '0', end = '1'
            positions.append((int(start), int(end)))  # positions = [(0, 1)]
        result[emote_id] = positions  # result = {'emote1': [(0, 1), (2, 3), (4, 5), (8, 9)]}
    return result  # result = {'emote1': [(0, 1), (2, 3), (4, 5), (8, 9)], 'emote2': [(6, 7)]}


def is_emote_only(
        content: str,
        emotes: Dict[str, List[Tuple[int, int]]]
) -> bool:
    emotes_count: int = 0
    emotes_length: int = 0
    for positions in emotes.values():
        emotes_count += len(positions)
        for start, end in positions:
            emotes_length += end - start + 1
    # if length of all emotes + count of space between each emote equals all content -> is emotes only
    return emotes_length + (emotes_count - 1) == len(content)


def parse_raw_badges(
        badges: str
) -> Dict[str, str]:
    if not badges:
        return {}
    result = {}
    # for exampe: badges = 'predictions/KEENY\sDEYY,vip/1'
    for badge in badges.split(','):  # badge = 'predictions/KEENY\\sDEYY' from ('predictions/KEENY\sDEYY', 'vip/1')
        key, value = badge.split('/', 1)  # key = 'predictions', value = 'KEENY\sDEYY'
        result[key] = value  # result = {'predictions': 'KEENY DEYY'}
    return result  # result = {'predictions': 'KEENY DEYY', 'vip': '1'}


def unescape_tag_value(
        value: str
) -> str:
    r"""
    Unescapes escaped value: '\s' -> ' ', '\:' -> ';', '\\' -> '\', '\' -> ''.
    '\r' and '\n' (CR and LF) don't need to be unescaped
    """
    if value:
        i = 0
        value = list(value)  # some symbols would be removed, simplier to do that with list
        while i < len(value) - 1:
            if value[i] == '\\':
                value.pop(i)  # important: after the pop [i+1] would be [i]
                if value[i] == 's':  # if '\s' replace to ' '
                    value[i] = ' '
                elif value[i] == ':':  # if '\:' replace to ';'
                    value[i] = ';'
                elif value[i] == '\\':  # if '\\' replace to '\'
                    pass
            i += 1
        else:
            if value[-1] == '\\':  # delete last slash if exists
                value.pop()
    return ''.join(value)  # return str
