# parts = ('first', 'second', 'third', 'fourth')
# parts = enumerate(parts)
# print(next(
#             (part for idx, part in parts if part.startswith('t')),
#             None
#         ))

# print(None)

# a = '12345678960'
# print(a[0:0] == '')
# print(a[0:0])
# print(a.split('1', 1))

# def split(text: str, separator: str, max_seps = 0):
#     '''
#     Function splits text every separator

#     Arguments:
#     text - string to split
#     separator - string by which text will be splitted
#     max_seps - max count of seporation (n - seporation, n+1 parts of text)
#     '''
#     # get len of separator
#     sep_len = len(separator)
#     # if len is 0, it must be Exception
#     # but better we just return whole string
#     if sep_len == 0:
#         yield text
#         return 
#     # counter counts times we separated string
#     counter = 0
#     # i - just index of letter in str
#     i = 0
#     # simple condition, for check whole string
#     # we need (i+sep_len) in condition
#     # for don't get IndexError - Exception 
#     #
#     # example: if len of text = 5, len of sep = 2,
#     # then the last index we'll can check is 4,
#     # and in the 28th row we'll get text[4:6],
#     # but we haven't 5th index of text, so we'll get Exception
#     while i+sep_len <= len(text):
#         #look for separator in text 
#         if text[i:i+sep_len] == separator:
#             # after find, yield all before separator
#             yield text[:i]
#             counter += 1
#             # if counts of times we separated parts equals max(from args)
#             # we need to stop this generator, and yield rest text
#             if counter == max_seps:
#                 yield text[i+sep_len:]
#                 return
#             # if we continue we need to delete previous part and separator from text
#             text = text[i+sep_len:]
#             # we've deleted previous part, 
#             # so we need to continue searching from 0th index 
#             i = 0
#         # just increase the index
#         i += 1
#     yield text
#     # without comments it looks simpler


# test = text.split(':')
# for part in split(text, ':'):
#     print(part == test[0])
#     test.pop(0)
# print(len(test))


# text2 = '123:123:'

# from time import time

# t0 = time()
# [part for part in text.split(':')]
# print(time()-t0)

# t1 = time()
# [part for part in split(text, ':')]
# print(time()-t1)

# for i in split(text2, ':', 2):
#     print(i)

# import asyncio
# import random

# async def test(number):
#     i = 0
#     while i < 10:
#         if number != 8:
#             sleep = random.randint(1,3)
#         else:
#             sleep = 6
#         print(f'I am {number}th, get {i}, will sleep {sleep}')
#         i += 1

#         await asyncio.sleep(sleep)

# async def main(loop):
#     for i in range(10):
#         loop.create_task(test(i))
#     # async for i in test():
#     #     print(f'First: {i}')
#     #     async for y in test():
#     #         print(f'Second: {y}')
# loop = asyncio.get_event_loop()
# loop.create_task(main(loop))
# loop.run_forever()
# loop.close()


# abcd = {123: '321', 12 : '21', 1 : '0', 'a': 220}

# print(abcd.keys())

# abcd = [-1, 0, 1, 2, 3]
# for value in abcd:
#     print(bool( int(value)+1 ))

# import copy

# a = [1, 2, 3, 'a', 'b', 'c', (4, 5, 6, 'd', {7: 'e', 8: 'f', 9: 'i'})]

# b = copy.copy(a)
# print(id(a), id(b))
# print(a is b)
# print(id(a[0]), id(b[0]))
# print(a[0] is b[0])
# print(a[6] is b[6])
# print(a[6][0] is b[6][0])
# print(a[6][4] is b[6][4])

# def parse_badge(badges: str):
#     result = {}
#     for badge in badges.split(','):
#         key, value = badge.split('/', 1)
#         result[key] = value
#     return result


# print(badges)


# import ttd
# import asyncio
# ttd.check(asyncio.get_event_loop())


# print(bool(None))
# from time import time
# a = r'\\s\s\\:\:\s\:\s\:\s\:\s\:\s\:\:\s\:\:\:'
# a = a * 10

# def replace_slashes(string: str):
#     string = list(string)
#     i = 0
#     while i < len(string):
#         if string[i] == '\\':
#             if string[i+1] == 's':
#                 string[i] = ' '
#                 string.pop(i+1)
#             elif string[i+1] == ':':
#                 string[i] = ';'
#                 string.pop(i+1)
#             elif string[i+1] == '\\':
#                 string.pop(i+1)
#         i+=1
#     return ''.join(string)
# t0 = time()
# print(replace_slashes(a))
# print(time() - t0)
# t0 = time()
# replace_slashes(a)
# print(time() - t0)


#
# def parse_raw_emotes(emotes: str):
#     result = {}
#     for emote in emotes.split('/'):
#         if not emote:
#             return
#         emote, positions = emote.split(':')
#         poss = [] # final positions list
#         positions = positions.split(',')
#         for pos in positions:
#             first, last = pos.split('-')
#             poss.append(int(first))
#             poss.append(int(last))
#         result[int(emote)] = poss
#     return result

# print(parse_raw_emotes('25:0-4,12-16,24-28/1902:6-10,18-22,30-34/30259:36-42,47-53/555555558:44-45,55-56'))


# class C(object):
#     def __init__(self):
#         pass

#     @property
#     def x(self):
#         """I'm the 'x' property."""
#         print("getter of x called")
#         return self._x

#     @x.setter
#     def x(self, value):
#         print("setter of x called")
#         self._x = value

#     @x.deleter
#     def x(self):
#         print("deleter of x called")
#         del self._x


# c = C()
# c.x = 'fooa'  # setter called
# foo = c.x # getter called
# print(foo)   
# del c.x      # deleter called

# from asyncio.coroutines import iscoroutine, iscoroutinefunction

# async def haha():
#     pass
# print(iscoroutine(haha))
# print(iscoroutinefunction(haha))


# def hello():
#     print('hello')

# class some:
#     def __init__(self) -> None:
#         pass

# something = some()
# try:
#     print(bool(something.hello))
# except AttributeError:
#     print(':( we have not that atr ):')


# setattr(something, 'hello', hello)
# something.hello()

# a = {1: ['a', 'b'], 2: ['c', 'd']}
#
# for b in a:
#     print(b)
#
# print(id)
# import re
#
# with open('TMP.txt', encoding="utf8") as file:
#     text = file.read()
#     regul = r'<a[^>]*tw-full-width tw-link tw-link--hover-underline-none ' \
#             r'tw-link--inherit[^>]*href="https://www.twitch.tv/([^"]*)[^>]*>'
#     result = re.findall(regul, text)
#     print(result)
#     print(len(result))

# import asyncio
# import aiohttp
#
# token = 'oauth:uitby99w18qo4n3jngs8bc754wjj4z'
# nick = 'rows_s'
#
#
# async def trys():
#     headers = {'Authorization': 'Bearer i8x4nlyyhvczit21cw6q6vogn5bebn',
#                'Client-Id': 'qatjkmub3mjti75up3vx3d4f3s1z33'}
#     async with aiohttp.ClientSession(headers=headers) as session:
#         url = 'https://id.twitch.tv/oauth2/validate'
#         async with session.get(url) as response:
#             print("Status:", response.status)
#             print("HEADERS:", response.headers)
#             print('TYPE:', response.content_type)
#             print(await response.text())
#         url = 'https://api.twitch.tv/helix/search/channels'
#         async with session.get(url + '?broadcaster_id=192827780') as response:
#             print(await response.json())
#
# asyncio.get_event_loop().run_until_complete(trys())

# while True:
#     tmp = input('===>  ')
#     print('===<   ', tmp.replace(' ', '_').lower())

# print(bool({}))

#
# import asyncio


# async def gener():
#     a = 2
#     while True:
#         a = yield a
#         if a is None:
#             a = 2
#         a += 1
#
#
# async def to_do():
#     # gen = gener()
#     # a = None
#     # while True:
#     #     a = await gen.asend(a)
#     #     print(a)
#     #     a = int(input())
#     gen = gener()
#     a = None
#     async for a in gen:
#         print(a)
#         a = await gen.asend(int(input()))
#         print(a)
#
# asyncio.get_event_loop().run_until_complete(to_do())


# single request:
# try:
#     response = await get_top_games(1).__anext__()
# except StopAsyncIteration:
#     do_someting()

# multiple requests:
# async for response in get_top_games(some_limit):
#     do_someting()

# multiple requests out of for:
# agenerator = get_top_games(**params)
# try:
#     response1 = await agenerator.__anext__()
#     response2 = await agenerator.__anext__()
# except StopAsyncIteretor:
#     do_something()
# While condition:
#     try:
#         responseN = await agenerator.__anext__()
#     except StopAsyncIteretor:
#         do_something()

# class Some:
#     def __str__(self):
#         return 'Some string from  Some-class without some args'
#
#     def __repr__(self):
#         return 'Some string from  Some-class without some args'
#
#
# a = [{'haha': ['asd', 'asdad', {12: 'b', 'list': ['some', 'two']}]},
#      'print',
#      'this',
#      ['second'],
#      {'hoho': ['1', '2'], 'php': {'no': 'yes', 1: Some()}}, Some()]
#
# print(str(a))
# broadcaster_id = None
# data = {
#     'broadcaster_id':  b
# }

# from random import random, randint
# from time import time
#
# some = {}
# t0 = time()
# for i in range(10000000):
#     some[randint(0, 10000000)] = randint(0, 1000)
# print('Dict created for', time()-t0)
# print(len(some))
# t0 = time()
# counter = 0
# keys = list(some.keys())
# print('Keys created for', time()-t0)
# t0 = time()
# for part in keys:
#     if some[part] > 500:
#         counter += 1
#         some.pop(part)
# print('pops done for', time()-t0, counter)

# some = {'tag_id': 123123}
# print(some)
#
# def hohoho(some: dict):
#     some = {'tag_id': [some['tag_id']]}
#     print(some)
#
# hohoho(some)
# print(some)

# from collections import namedtuple
#
# Some_human = namedtuple('Human', ['first_name', 'second_name', 'age', 'gender'])
# an_human = Some_human
#
# me = an_human('Vladimir', 'Marmuz', '18', 'M')
#
# print(me.first_name,           # Vladimir
#       me.second_name,          # Marmuz
#       me.age,                  # 18
#       me.gender,               # M
#       type(me).__name__,       # Human
#       type(me) == Some_human)  # True
#
# from collections import namedtuple
#
# Some_human = namedtuple('Human', ['first_name', 'second_name', 'age', 'gender'])
#
# me = Some_human('Vladimir', 'Marmuz', '18', 'M')
#
# print(me.first_name,      # Vladimir
#       me.second_name,     # Marmuz
#       me.age,             # 18
#       me.gender,          # M
#       type(me).__name__)  # Human


# path = r"D:\Users\I3rowser\Desktop\to distribute\py-twitch\src\api.py"
#
# import re
#
# with open(path) as file:
#     text = file.read()
#     reg = r"(if ([\w]*) is not None:\n[ ]*(data|params)\['[\w]*'\] = [\w]*)"
#     results = re.findall(reg, text)
#     for result in results:
#         reg = f"({result[1]})"
#         text = result[0]
#         finded = re.findall(reg, text)
#         if len(re.findall(reg, text)) != 3:
#             print('\nError\n', result)
#
# from aiohttp import web
# from aiohttp.web import BaseRequest
# import hmac
# import hashlib

# secret = b'jdrvhrxgx5vnehmbkrks9f20mxift3'
#
#
# async def twitch_event_handler(request: BaseRequest):
#     hmac_message = request.headers.get('Twitch-Eventsub-Message-Id') \
#                    + request.headers.get('Twitch-Eventsub-Message-Id')\
#                    + await request.text()
#     signature = hmac.new(secret, bytes(hmac_message, 'utf-8'), hashlib.sha256)
#     print(signature.hexdigest() == request.headers.get('Twitch-Eventsub-Message-Signature'))
#     if request.headers.get('Twitch-Eventsub-Message-Type') == 'webhook_callback_verification':
#         json = await request.json()
#         return web.Response(text=json['challenge'])
#     elif request.headers.get('Twitch-Eventsub-Message-Type') == 'notification':
#         json = await request.json()
#         if json['subscription']['type'] == 'channel.follow':
#             print('Get some Follow!', json, sep='\n')
#         elif True:
#             pass
#
# app = web.Application()
# app.add_routes([web.post('twitch/events/subscriptions', event_listener)])
#
#
# web.run_app(app, port=9028)


# secret = b'k787mojuorcyvwvz5421zvo9eya3m6'
# ID = '1c017831-7838-42dd-a8d3-e6a97d47d332'
# time = '2021-01-09T13:11:22Z'
# text = '{"subscription":{"id":"d1a33748-ed6f-4ed4-968c-83eaf7752ce2","status":"webhook_callback_verification_pending","type":"channel.follow","version":"1","condition":{"broadcaster_user_id":"192827780"},"transport":{"method":"webhook","callback":"https://6516fa7e95d9.ngrok.io/twitch/events/subscriptions"},"created_at":"2021-01-09T13:11:22.185250699Z"},"challenge":"r-fAHCNXbEsgfNCkP0MaJ2ulykKkkeixFkCP_qshkGg"}'
# hmac_message = ID + time + text
#
# signature = hmac.new(secret, bytes(hmac_message, 'utf-8'), hashlib.sha256)
# print('sha256=', signature.digest(), sep='')
# print('encode=', signature.hexdigest(), sep='')
# print('93029f95d27812115684f38d3d7deb9498fd3b205b4307d7b2055b10ac44ffac' == signature.hexdigest())

# from api import Api
# import aiohttp
# import asyncio
#
# from aiohttp import web
# from aiohttp.web import BaseRequest
# import hmac
# import hashlib
#
# import config


# async def twitch_event_handler(request: BaseRequest):
#     print('>>>> headers= "', request.headers, sep='', end='"!\n\n')
#     ID = request.headers.get('Twitch-Eventsub-Message-Id')
#     time = request.headers.get('Twitch-Eventsub-Message-Timestamp')
#     body = await request.text()
#     print('>>>> body= "', body, sep='', end='"!\n\n')
#     message_bytes = bytes(ID + time + body, 'utf-8')
#     signature = hmac.new(bytes(config.secret, 'utf-8'), message_bytes, hashlib.sha256).hexdigest()
#     print('sha256=' + signature == request.headers.get('Twitch-Eventsub-Message-Signature'))
#     if request.headers.get('Twitch-Eventsub-Message-Type') == 'webhook_callback_verification':
#         json = await request.json()
#         return web.Response(text=json['challenge'])
#     elif request.headers.get('Twitch-Eventsub-Message-Type') == 'notification':
#         json = await request.json()
#         if json['subscription']['type'] == 'channel.follow':
#             print('Get some Follow!', json, sep='\n')
#         elif True:
#             pass
#
# app = web.Application()
# app.add_routes([web.post('/twitch/events/subscriptions', twitch_event_handler),
#                 web.get('/twitch/events/subscriptions', twitch_event_handler)])
#
# web.run_app(app, port=8080)

# class HiMan:
#     def __init__(self, a: int):
#         self.numb = a
#         self.double = a**2
#
#     async def print_me(self, add: int):
#         print(self.numb + add, self.double + add)
#
#
# async def handle(callback):
#     command = input('<<<<  ')
#     if command == 'printme':
#         await callback(2)
#
#
# async def printyou(self, deduct: int):
#     print(self.numb - deduct, self.double - deduct)
#
#
# if __name__ == '__main__':
#     first = HiMan(12)
#     # second = HiMan(15)
#     setattr(first, 'print_you', printyou)
#     callback = first.print_me
#     callback2 = first.print_you
#
#     print(callback.__code__.co_argcount)
#     asyncio.get_event_loop().run_until_complete(handle(callback))
#     asyncio.get_event_loop().run_until_complete(handle(callback2))

# import re
#
# path = r"D:\Users\I3rowser\Desktop\twitch.htm"
# start = '<div class="language-json highlighter-rouge"><div class="highlight"><pre class="highlight"><code><span class="p"'
# end = '</span><span class="w">\n</span></code></pre></div></div>'
# result = []
# with open(path) as file:
#     text = file.read()
#     for i in range(len(text)):
#         if text[i: i+len(start)] == start:
#             first = i+len(start)
#             for j in range(i + 1, len(text)):
#                 if text[j: j+len(end)] == end:
#                     i = j+len(end)
#                     result.append(text[first:j])
#                     break
#
# exc = '>([^<]*)<'
# final = []
# for text in result:
#     final.append(''.join(re.findall(exc, text)))
#
# final_result = [text for text in final if '"subscription"' in text]
# for text in final_result:
#     print(text)
# print(len(final_result))

# import config
# from api import Api
# import asyncio
# import errors
# from utils import normalize_ms
# import random
# import string
# import time
# api = Api()
#
#
# async def check():
#     print('\n===================\n')
#     try:
#         async for event in api.get_eventsub_subscriptions(100):
#             for key in event:
#                 print(f'{key}: {event[key]}')
#             print(event)
#     except Exception as e:
#         print(e)
#         await Api.close()
#         quit(0)
#
#
#
# async def delete():
#     print('\n===================\n')
#     async for event in api.get_eventsub_subscriptions(100):
#         event_id = event['id']
#         await api.delete_eventsub_subscription(event_id)
#         print(f'Deleted - {event_id}')
#
#
# async def create():
#     stream = api.get_streams(1)
#     print(stream)
#     async for stream in api.get_streams(1):
#         print(stream)
#     top_streamer = await api.once(api.get_streams(1))
#     top_streamer = top_streamer['id']
#     callback = 'https://3927597a0532.ngrok.io/twitch/events/subscriptions'
#     url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
#     json = {
#         'type': 'channel.follow',
#         'version': '1',
#         'condition': {
#             'broadcaster_user_id': '192827780'
#         },
#         'transport': {
#             'method': 'webhook',
#             'callback': callback,
#             'secret': config.secret
#         }
#     }
#     try:
#         response = await api._http_post(url, json, {})
#     except errors.HTTPError as res:
#         response = res.args[0]
#     print('\n===================\n')
#     for some in response:
#         print(some, response[some], sep=' : ')
#     print('ID:', top_streamer)
#
#
# async def somain():
#     await api.set_token(config.app_token)
#     create_str = lambda: (''.join(random.choices(string.ascii_uppercase, k=10)),
#                           ''.join(random.choices(string.ascii_uppercase, k=5)))
#     many_strs = None
#
#     while True:
#         do = input('\n>>>>\n    ')
#         if do == 'checkall':
#             await check()
#         elif do == 'deleteall':
#             await delete()
#         elif do == 'createone':
#             await create()
#         elif do == 'stop':
#             await Api.close()
#             break
#
#         elif do == 'normdate':
#             print(normalize_ms('2021-01-13T13:26:02'))
#             print(normalize_ms('2021-01-13T13:26:02Z'))
#             print(normalize_ms('2021-01-13T13:26:02.123456Z'))
#             print(normalize_ms('2021-01-13T13:26:02.12345612312Z'))
#             print(normalize_ms('2021-01-13T13:26:02.1234Z'))
#         elif do == 'except':
#             try:
#                 a, b = None
#             except Exception as e:
#                 print(type(e), e)
#         elif do == 'testpop':
#             some_list = [0, 1, 2, 3, 4, 5, 6, 7, 8]
#             while len(some_list):
#                 print(some_list)
#                 some_list.pop(0)
#             print(some_list)
#
#             some_list = [0, 1, 2, 3, 4, 5, 6, 7, 8]
#             for i in some_list:
#                 print(some_list, i)
#                 some_list.pop(0)
#             print(some_list)
#         elif do == 'none':
#             try:
#                 None[0]
#             except Exception as e:
#                 print(type(e), e)
#         elif do == 'strIndexError':
#             try:
#                 a = 'asf'[2:4]
#                 print(a)
#                 print('abc'.split('c'))
#             except Exception as e:
#                 print(type(e), e)
#         elif do.startswith('tryVSif'):
#             try:
#                 multiplier = float(do.split()[1])
#             except (IndexError, ValueError):
#                 multiplier = 2
#             default = 10
#             multed = default * multiplier
#             long = {str(i): i**i for i in range(0, default)}
#             excepts = 0
#             dones = 0
#             t0 = time.time()
#             for _ in range(100000):
#                 i = random.randint(0, multed-1)
#                 try:
#                     tmp = long[str(i)]
#                 except KeyError:
#                     excepts += 1
#                 else:
#                     dones += 1
#             print('try in loop', time.time()-t0, dones, excepts)
#             excepts = 0
#             dones = 0
#             t0 = time.time()
#
#             for _ in range(100000):
#                 i = random.randint(0, multed-1)
#                 tmp = long.get(str(i))
#                 if tmp is None:
#                     excepts += 1
#                 else:
#                     dones += 1
#             print('if in loop', time.time()-t0, dones, excepts)
#         elif do == 'replace':
#             def replace_slashes(text: str):
#                 """
#                 some parent content will contains (space), (slash), (semicolon)
#                 which will be replaced as (space) to (slash+s), (slach) to (slash+slach), (semicolon) to (slash+colon)
#                 in this function we are replacing all back
#                 """
#                 text = list(text)  # work with list will be easier
#                 i = 0  # simple current index
#                 while i < len(text):
#                     if text[i] == '\\':
#                         if text[i + 1] == 's':  # if '\s' replace to ' '
#                             text[i] = ' '
#                             text.pop(i + 1)
#                         elif text[i + 1] == ':':  # if '\:' replace to ';'
#                             text[i] = ';'
#                             text.pop(i + 1)
#                         elif text[i + 1] == '\\':  # if '\\' replace to '\'
#                             text.pop(i + 1)
#                         # above we change first letter and delete second
#                         # That's needed do not replace one letter twice
#                     i += 1
#                 return ''.join(text)  # return joined list
#             main = ''.join(random.choices(['\\', ' ', ';', '!', 's', ':'], k=2000))
#             for i in range(0, 2000, 100):
#                 print(main[i: i+100])
#             # main = r'\\ ;..\.z; ;\'
#             not_main = r'\\\\\s\:..\\.z\:\s\:\\'
#             print(not_main.replace('\\s', ' ').replace('\\:', ';').replace('\\\\', '\\'))
#
#
#
# # exc = r'([\d]{4})-([\d]{2})-([\d]{2})T([\d]{2}):([\d]{2}):([\d]{2}).([\d]{6})'
#
# asyncio.get_event_loop().run_until_complete(somain())

# class Base:
#     def __init__(self):
#         self.hello = 'hello'
#
#
# def bh():
#     print(self.hello)
#
#
# b = Base()
# setattr(b, 'bh', bh)
# b.bh()

# class Base:
#     def __init__(self):
#         self.hello = 1
#
#     def send(self):
#         print(self.hello)
#
#
# class Bb:
#     def __init__(self, callback):
#         self.call = callback
#
#
# a = Base()
# b = Bb(a.send)
# b.call()
# a.hello = 2
# b = Bb(a.send)
# b.call()

# import random
# import asyncio
# from irc_client import Client
# from irc_channel import Channel
# from time import time
#
# tags = {'emote-only': '0', 'followers-only': '15', 'r9k': '0', 'rituals': '0',
#         'room-id': '192827780', 'slow': '0', 'subs-only': '0'}
# command = ['tmi.twitch.tv', 'ROOMSTATE', '#rows_s']
#
# class Client1(Client):
#     def _handle_roomstate1(self, tags: dict, command: list):
#         def handle_new_channel(tags, command):
#             channel_login = command[-1][1:]
#             # create channel
#             channel = Channel(channel_login, self.send_message, tags)
#             # insert my_state if exists
#             my_state = self._local_states.pop(channel_login, None)
#             if my_state is not None:
#                 channel.my_state = my_state
#             # insert nameslist if exists
#             nameslist = self._channels_nameslists.pop(channel_login, None)
#             if type(nameslist) == tuple:
#                 channel.nameslist = nameslist
#             # save channel
#             self._unprepared_channels[channel_login] = channel
#             # save if ready
#             if self._is_channel_ready(channel_login):
#                 self._save_channel(channel_login)
#
#         if len(tags) == 7:  # new channel
#             handle_new_channel(tags, command)
#         elif len(tags) == 2:  # channel update
#             self.handle_channel_update(tags, command)
#
#         def _handle_roomstate(self, tags: dict, command: list):
#             if len(tags) == 7:  # new channel
#                 self.handle_new_channel(tags, command)
#             elif len(tags) == 2:  # channel update
#                 self.handle_channel_update(tags, command)
#
#         def handle_new_channel(self, tags, command):
#             channel_login = command[-1][1:]
#             # create channel
#             channel = Channel(channel_login, self.send_message, tags)
#             # insert my_state if exists
#             my_state = self._local_states.pop(channel_login, None)
#             if my_state is not None:
#                 channel.my_state = my_state
#             # insert nameslist if exists
#             nameslist = self._channels_nameslists.pop(channel_login, None)
#             if type(nameslist) == tuple:
#                 channel.nameslist = nameslist
#             # save channel
#             self._unprepared_channels[channel_login] = channel
#             # save if ready
#             if self._is_channel_ready(channel_login):
#                 self._save_channel(channel_login)
#
# async def start():
#     a = Client1()
#     t0 = time()
#     for _ in range(1000000):
#         a._handle_roomstate1(tags, command)
#     print(time()-t0)
#     t0 = time()
#     for _ in range(1000000):
#         a._handle_roomstate(tags, command)
#     print(time()-t0)
#
# asyncio.get_event_loop().run_until_complete(start())
# from time import time
#
# def outer():
#     def inner():
#         print(id(inner))
#     inner()
# t0 = time()
# for _ in range(10):
#     outer()
# print(time()-t0)

# def inner():
#     pow(2, 2)
# def outer():
#     inner()
# t0 = time()
# for _ in range(1000000):
#     outer()
# print(time()-t0)

# from typing import NamedTuple, Callable
# from dataclasses import dataclass
#
# @dataclass()
# class SingleRequest:
#     # return_handler: Callable = lambda json: json['data'][0] if (json is not None) else json
#     return_handler: Callable = lambda _: (_ for _ in ()).throw(NotImplementedError('http_method must passed'))
#
#
# def do(request: SingleRequest):
#     response = {'data': [12, 15]}
#     return request.return_handler(response)
#
#
# def foo(json):
#     return json['data']
#
#
# print(do(SingleRequest()))
# print(do(SingleRequest(lambda json: json['data'])))
# a = SingleRequest()
# print(do(a))
# a.return_handler = lambda json: json['data']
# print(do(a))

# from dataclasses import dataclass

