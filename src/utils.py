<<<<<<< Updated upstream
from typing import Dict, List
=======
from typing import Dict, List, Iterable, Any, Union, Tuple
>>>>>>> Stashed changes


def split(text: str, separator: str, max_seps=0):
    """
    Function splits text every separator
    Arguments:
    text - str to split
    separator - str by that text will be splitted
    max_seps - max count of seporation (n - seporation = n+1 parts of text)
    """
    # get len of separator
    sep_len = len(separator)
    # if len is 0, it must be Exception
    # but better we just return whole string
    if sep_len == 0:
        yield text
        return
        # counter counts times we separated string
    counter = 0
    # i - just index of letter in str
    i = 0
    # simple loop, for check whole string
    while i + sep_len <= len(text):
        # look for separator in text
        if text[i:i + sep_len] == separator:
            # after find, yield all before separator
            yield text[:i]
            counter += 1
            # if counts of times we separated parts equals max(from args)
            # we need to stop this generator, and yield rest text
            if counter == max_seps:
                yield text[i + sep_len:]
                return
            # if we continue we need to delete previous part and separator from text
            text = text[i + sep_len:]
            # we've deleted previous part, 
            # so we need to continue searching from 0th index 
            i = 0
        # just increase the index
        i += 1
    yield text
    # without comments it looks simpler


def is_int(string: str) -> bool:
    try:
        int(string)
        return True
    except ValueError:
        return False


def parse_raw_tags(prefix: str) -> Dict[str, str]:
    tags = {}  # we'll return tags
    i = 0  # simple current index of `tag_name` searching
    last = 0  # position of end of last `tag_value` + 1
    while i < len(prefix):
        # if we found '=' - all before is `tag_name`
        if prefix[i] == '=':
            tag_name = prefix[last:i]
            j = i + 1  # simple current index of `tag_value` searching
            while j < len(prefix):
                # if we found ';' - all between '='(i) and ';'(j) is tag_value
                if prefix[j] == ';':
                    tag_value = prefix[i + 1:j]
                    tags[tag_name] = tag_value
                    i = last = j + 1
                    break
                j += 1
            # the last tag hasn't ';' in end, so just take all
            else:
                tag_value = prefix[i + 1:]
                tags[tag_name] = tag_value
                break
        i += 1
    return tags


def parse_raw_emotes(emotes_str: str) -> Dict[str, List[Tuple[int, int]]]:
    result = {}  # to return
    # all emoted separated by '/'
    for emote in emotes_str.split('/'):
        # we can get empty str-'', if so return
        if not emote:
            return result
        emote_id, raw_positions = emote.split(':', 1)  # emote_id and emote_positions separated by ':'
        positions = raw_positions.split(',')  # all pair of positions separated by ','
        parsed_positions = []  # final positions list
        # loop to handle all positions of current emote
        for position in positions:
            # start and end of a pair separeted by '-', looks like '2-4'
            # every position looks like '2-4',
            start, end = position.split('-')
            parsed_positions.append(
                (int(start), int(end))  # Tuple[int, int]
            )
        result[emote_id] = parsed_positions  # insert emote_id: positions into result
    return result


def parse_badge(badges: str) -> Dict[str, str]:
    result = {}  # to return
    # every bage/value separated by ','
    for badge in badges.split(','):
        # # we can get empety str, if so - skip
        if badge:
            # every bage & value separated by '/'
            key, value = badge.split('/', 1)
            result[key] = value
    return result


def replace_slashes(text: str):
    """
    some parent content will contains (space), (slash), (semicolon)
    which will be replaced as (space) to (slash+s), (slach) to (slash+slach), (colon) to (slash+colon)
    in this function we replacing all back \n
    """
    print('!!!\n>>>>', text)
    text = list(text)  # work with list will be easier
    i = 0  # simple current index
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
            # above we change first letter and delete second
            # That's needed do not replace one letter twice
        i += 1
<<<<<<< Updated upstream
    return ''.join(text)
=======
    result = ''.join(text)
    print('!!!\n>>>>', result)
    return result  # return joined list


def normalize_ms(date: str):
    if date.endswith('Z'):
        date = date[:-1]
    dot_index = date.find('.')
    if dot_index != -1:
        after_dot = len(date) - dot_index - 1
        if after_dot > 6:
            date = date[:dot_index+7]
        else:
            date += ('0' * (6 - after_dot))
    else:
        date = date + '.000000'
    return date

>>>>>>> Stashed changes
