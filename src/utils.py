def split(text: str, separator: str, max_seps = 0):
    '''
    Function splits text every separator
    
    Arguments:
    text - string to split
    separator - string by which text will be splitted
    max_seps - max count of seporation (n - seporation, n+1 parts of text)
    '''
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
    while i+sep_len <= len(text):
        #look for separator in text 
        if text[i:i+sep_len] == separator:
            # after find, yield all before separator
            yield text[:i]
            counter += 1
            # if counts of times we separated parts equals max(from args)
            # we need to stop this generator, and yield rest text
            if counter == max_seps:
                yield text[i+sep_len:]
                return
            # if we continue we need to delete previous part and separator from text
            text = text[i+sep_len:]
            # we've deleted previous part, 
            # so we need to continue searching from 0th index 
            i = 0
        # just increase the index
        i += 1
    yield text
    # without comments it looks simpler