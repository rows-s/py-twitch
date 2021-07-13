import pytest
from twitch.utils import *
from twitch.irc.utils import *


def test_parse_raw_emotes():
    raw_emotes1 = 'emote1:0-1,2-3,4-5,8-9/emote2:6-7'
    emotes1 = {'emote1': [(0, 1), (2, 3), (4, 5), (8, 9)], 'emote2': [(6, 7)]}

    raw_emotes2 = '425618:0-2,4-6,8-10,12-14,16-18'
    emotes2 = {'425618': [(0, 2), (4, 6), (8, 10), (12, 14), (16, 18)]}

    raw_emotes3 = '302167490:0-9,11-20,22-31,33-42,44-53,55-64,66-75,77-86,88-97,99-108,110-119,121-130,132-141,143-152,154-163'
    emotes3 = {'302167490': [(0, 9), (11, 20), (22, 31), (33, 42), (44, 53), (55, 64), (66, 75), (77, 86), (88, 97),
                             (99, 108), (110, 119), (121, 130), (132, 141), (143, 152), (154, 163)]}

    raw_emotes4 = '555555584:126-127,143-144,160-161,177-178/145315:0-12,14-26,28-40,42-54,56-68,70-82,84-96,98-110,112-124,129-141,146-158,163-175'
    emotes4 = {'555555584': [(126, 127), (143, 144), (160, 161), (177, 178)],
               '145315': [(0, 12), (14, 26), (28, 40), (42, 54), (56, 68), (70, 82),
                          (84, 96), (98, 110), (112, 124), (129, 141), (146, 158), (163, 175)]}
    assert parse_raw_emotes('') == {}
    assert parse_raw_emotes(raw_emotes1) == emotes1
    assert parse_raw_emotes(raw_emotes2) == emotes2
    assert parse_raw_emotes(raw_emotes3) == emotes3
    assert parse_raw_emotes(raw_emotes4) == emotes4


def test_is_emote_only():
    assert is_emote_only(
        'LUL LUL LUL LUL LUL LUL LUL',
        {'425618': [(0, 2), (4, 6), (8, 10), (12, 14), (16, 18), (20, 22), (24, 26)]}
    )
    assert not is_emote_only(
        'LUL LUL LUL LUL LUL LUL LUL',
        {'425618': [(0, 2), (4, 6), (8, 10), (12, 14), (16, 18), (20, 22)]}
    )
    assert is_emote_only(
        'SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc straydotaGoose',
        {
            '304273555': [(54, 67)], '52': [(0, 4), (6, 10), (12, 16), (18, 22), (24, 28), (30, 34), (36, 40), (42, 46), (48, 52)]
        }
    )
    assert not is_emote_only(
        'SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc SMOrc straydotaGoose' + 'a word',
        {
            '304273555': [(54, 67)], '52': [(0, 4), (6, 10), (12, 16), (18, 22), (24, 28), (30, 34), (36, 40), (42, 46), (48, 52)]
        }
    )
    assert not is_emote_only(
        'les petite filles de 14 ans oui, la drogue non chowcsgoMOUE',
        {'301906773': [(47, 58)]})


def test_parse_raw_badges():
    assert parse_raw_badges('predictions/KEENY\\sDEYY,vip/1') == {'predictions': 'KEENY DEYY', 'vip': '1'}
    assert parse_raw_badges('vip/1,subscriber/6,glitchcon2020/1') == {
        'vip': '1', 'subscriber': '6', 'glitchcon2020': '1'
    }
    assert parse_raw_badges('moderator/1,subscriber/36,partner/1') == {
        'moderator': '1', 'subscriber': '36', 'partner': '1'
    }


def test_unescape_tag_value():
    assert unescape_tag_value(r'\s\\\:\\s\\\\\\:') == r' \;\s\\\:'
    assert unescape_tag_value(r'axozerTem\sato\saxozerPium\saxozerPium_HF') == 'axozerTem ato axozerPium axozerPium_HF'
    assert unescape_tag_value(r'\s\\\:\s\\s\:.s\\\:asd\:\\as]\:\\\:\sqwe\\\:') == r' \; \s;.s\;asd;\as];\; qwe\;'
    assert unescape_tag_value('\\') == ''
    assert unescape_tag_value('some word\\') == 'some word'
    assert unescape_tag_value('some\\word') == 'someword'


def test_normalize_ms():
    base = '2021-01-13T13:26:02'
    assert normalize_ms(base) == base + '.0'
    assert normalize_ms(base + '.Z') == base + '.0'
    assert normalize_ms(base + '.123456Z') == base + '.123456'
    assert normalize_ms(base + '.123456123Z') == base + '.123456'
    assert normalize_ms(base + '.1234Z') == base + '.1234'
    assert normalize_ms(base + '.') == base + '.0'


def test_remove_not_valid_postfix():
    with pytest.raises(TypeError):
        remove_not_valid_postfix('', valid_symbols='', invalid_symbols='')
    with pytest.raises(TypeError):
        remove_not_valid_postfix('')
    valids = '-:.0123456789'
    assert remove_not_valid_postfix('-.:123123a', valid_symbols=valids) == '-.:123123'
    assert remove_not_valid_postfix('asda', valid_symbols=valids) == ''
    assert remove_not_valid_postfix('', valid_symbols=valids) == ''
    assert remove_not_valid_postfix('123.123', valid_symbols=valids) == '123.123'
    assert remove_not_valid_postfix('asdasdasdqweqsad1a', valid_symbols=valids) == 'asdasdasdqweqsad1'
    invalids = 'FOOBAZBAR'
    assert remove_not_valid_postfix('ABCD', invalid_symbols=invalids) == 'ABCD'
    assert remove_not_valid_postfix('BAZBARFOO', invalid_symbols=invalids) == ''
    assert remove_not_valid_postfix('BAZBARFOO_', invalid_symbols=invalids) == 'BAZBARFOO_'
    assert remove_not_valid_postfix('B_B', invalid_symbols=invalids) == 'B_'
