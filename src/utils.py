from typing import Dict, List


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


def prefix_to_dict(prefix: str) -> Dict[str, str]:
    tags = {}  # we'll return tags
    i = 0  # simple current index of <tag_name> searching
    last = 0  # position of end of last tag-value
    while i < len(prefix):
        # if we found '=' - all before is <tag_name>
        if prefix[i] == '=':
            key = prefix[last:i]
            j = i + 1  # simple current index of <tag_value> searching
            while j < len(prefix):
                # if we found ';' - all between '='(i) and ';'(j) is value
                if prefix[j] == ';':
                    value = prefix[i + 1:j]
                    tags[key] = value
                    i = last = j + 1
                    break
                j += 1
            # last tag has not ';' in end, so just take all
            else:
                value = prefix[i + 1:]
                tags[key] = value
        i += 1
    return tags


def emotes_to_dict(emotes: str) -> Dict[str, List[int]]:
    result = {}  # to return
    # all emoted separated by '/'
    for emote in emotes.split('/'):
        # we can get empty str-'', if so return
        if not emote:
            return result
        # emote_id and emote_positions separated by ':'
        emote, positions = emote.split(':')
        poss = []  # final positions list
        # all pair of positions separated by ','
        positions = positions.split(',')
        # loop to handle all positions of current emote
        for pos in positions:
            # every positions looks like '2-4', so...
            first, last = pos.split('-')
            poss.append(int(first))  # append first position
            poss.append(int(last))  # append last position

        result[emote] = poss  # insert emote_id: positions into result
    return result


def badges_to_dict(badges: str) -> Dict[str, str]:
    result = {}  # to return
    # every bage/value separated by ','
    for badge in badges.split(','):
        # # we can get empety str, if so - skip
        if badge:
            # every bage & value separated by '/'
            key, value = badge.split('/', 1)
            result[key] = value
    return result


def replace(text: str):
    """
    some parent content will contains (space), (slash), (semicolon)
    which will be replaced as (space) to (slash+s), (slach) to (slash+slach), (colon) to (slash+colon)
    in this function we replacing all back \n
    """
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
            # above we changing first letter and delete second
            # that's need to don't replace one letter twice
        i += 1
    return ''.join(text)
