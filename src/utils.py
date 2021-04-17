from typing import Dict, List, Tuple


def is_int(string: str) -> bool:
    try:
        int(string)
        return True
    except ValueError:
        return False


def parse_raw_tags(raw_tags: str) -> Dict[str, str]:
    tags = {}  # we'll return tags
    key_i = 0
    previous_tag_end = 0
    while key_i < len(raw_tags):
        if raw_tags[key_i] == '=':
            value_i = key_i + 1
            while value_i < len(raw_tags):
                if raw_tags[value_i] == ';':
                    tag_key = raw_tags[previous_tag_end:key_i]  # all between (';' || 0) and ('=') is `tag_key`
                    tag_value = raw_tags[key_i + 1:value_i]  # all between ('=') and (';') is `tag_value`
                    tags[tag_key] = tag_value
                    key_i = previous_tag_end = value_i + 1  # increment is needed so that `tag_key` does not contain ';'
                    break
                value_i += 1
            else:  # last tag has not ';' in end, so just take all
                tag_key = raw_tags[previous_tag_end:key_i]
                tag_value = raw_tags[key_i + 1:]
                tags[tag_key] = tag_value
        key_i += 1
    return tags


def parse_raw_emotes(emotes: str) -> Dict[str, List[Tuple[int, int]]]:
    if not emotes:
        return {}
    result = {}
    # for example: emotes = 'emote1:0-1,2-3,4-5,8-9/emote2:6-7'
    for emote in emotes.split('/'):  # emote = 'emote1:0-1,2-3,4-5,8-9'
        positions = []  # positions of current emote_id
        emote_id, raw_positions = emote.split(':', 1)  # emote_id = 'emote1', raw_positions = '0-1,2-3,4-5,8-9'
        for raw_position in raw_positions.split(','):  # raw_position = '0-1' # splited = ['0-1', '2-3', '4-5', '8-9']
            start, end = raw_position.split('-')  # start = '0', end = '1'
            positions.append((int(start), int(end)))  # positions = [(0, 1)]
        result[emote_id] = positions  # result = {'emote1': [(0, 1), (2, 3), (4, 5), (8, 9)]}
    return result  # result = {'emote1': [(0, 1), (2, 3), (4, 5), (8, 9)], 'emote2': [(6, 7)]}


def parse_raw_badges(badges: str) -> Dict[str, str]:
    if not badges:
        return {}
    result = {}
    # for exampe: badges = 'predictions/KEENY\sDEYY,vip/1'
    for badge in badges.split(','):  # badge = 'predictions/KEENY\\sDEYY' from ['predictions/KEENY\sDEYY', 'vip/1']
        key, value = badge.split('/', 1)  # key = 'predictions', value = 'KEENY\sDEYY'
        result[key] = replace_slashes(value)  # result = {'predictions': 'KEENY DEYY'}
    return result  # result = {'predictions': 'KEENY DEYY', 'vip': '1'}


def replace_slashes(text: str):
    """
    some parent content will contains (space), (slash), (semicolon)
    which will be replaced as (space) to (slash+s), (slash) to (slash+slach), (semicolon) to (slash+colon)
    in this function we are replacing all back
    """
    text = list(text)  # some symbols would be removed
    i = 0
    while i < len(text):
        if text[i] == '\\':
            if text[i + 1] == 's':  # if '\s' replace to ' '
                text[i] = ' '
                text.pop(i + 1)
            elif text[i + 1] == ':':  # if '\:' replace to ';'
                text[i] = ';'
                text.pop(i + 1)
            elif text[i + 1] == '\\':  # if '\\' replace to '\'
                text.pop(i + 1)
            # above we change current symbol and remove next symbol, so as not to replace one symbol twice
            # example: original = '\s', encoded = '\\s', decoding after 1st iteration = '\s'
            # 2nd iteration must not replace '\s' to ' '. And it doesn't, because `i` equals 1 (it's 's').
        i += 1
    return ''.join(text)  # return str


def normalize_ms(datetime_str: str):
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1]
    dot_index = datetime_str.find('.')
    if dot_index == -1:
        datetime_str = datetime_str + '.0'
    else:
        ms_symbols_length = len(datetime_str) - dot_index - 1
        if ms_symbols_length > 6:
            datetime_str = datetime_str[:dot_index + 7]  # length of milliseconds must not be more than 6
        elif ms_symbols_length == 0:
            datetime_str += '0'
    return datetime_str

