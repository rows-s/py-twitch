import asyncio
import websockets
from message import Message
from channel import *
from member import *
from copy import copy
from utils import is_int
from typing import Callable, Iterable
from errors import FuncIsNotCorutine, WrongFunctiomName

# our uri to connent to sever
uri = 'wss://irc-ws.chat.twitch.tv:443'

# class Client, it will create bots
class Client: 
    def __init__(self, token: str, login: str, channels: Iterable):
        self.token = token
        self.login = login
        self.channels = channels # channel-list to connect
        self.joined = {} # dict of Channel-object, see Channel-class
        self.ws = None
        self.event_loop = asyncio.get_event_loop()
        self.nick = None
        self.color = None
        self.id = None
        self.emotes = None
        self.badges = {}
        self.badges_info = {}
        # methods
        self.on_room_join = None
        self.on_room_update = None
        self.on_message = None
        self.on_login = None

    def event(self, function: Callable):
        # func must be corutine ( use async def ...)
        if not asyncio.iscoroutinefunction(function):
            raise FuncIsNotCorutine(function.__name__ + ' is not a corutine')
        if function.__name__ == 'on_room_update':
            self.on_room_update = function
        elif function.__name__ == 'on_login':
            self.on_login = function
        elif function.__name__ == 'on_room_join':
            self.on_room_join = function
        else:
            raise WrongFunctiomName


    async def send(self, command: str) -> None:
        await self.ws.send(command + '\r\n')
        if not command.startswith('PASS'):
            print('<', command)


    async def send_msg(self, channel: str, text: str) -> None:
        await self.send(f'PRIVMSG #{channel} :{text}')


    def run(self):
        async def start():
            # creating websocket
            self.ws = await websockets.client.connect(uri, loop=self.event_loop)
            # asking server to capability
            await self.send('CAP REQ :twitch.tv/commands')
            await self.send('CAP REQ :twitch.tv/membership')
            await self.send('CAP REQ :twitch.tv/tags')
            # loging
            await self.send(f'PASS {self.token}')
            await self.send(f'NICK {self.login}')
            # joining the channels
            for channel in self.channels:
                await self.send(f'JOIN #{channel}')
            
            # loop to receive, splite and handle messages we got
            while True:
                received_msgs = await self.ws.recv()
                for received_msg in received_msgs.split('\r\n'):
                    # sometimes we'll get more then 1 msg from server and
                    # if so - i like to create tasks and don't call them
                    # before we finish current loop
                    self.event_loop.create_task(self.handle_message(received_msg))
        # i don't know other way to make a event loop in function ;) So enjoy that
        self.event_loop.run_until_complete(start())


    async def handle_message(self, msg: str) -> None:
        # if we got empty msg - skip
        if len(msg) == 0:
            return
        print('>', msg)
        
        # sometimes (about once in 5 minutes) we'll get PING
        # that means server is checking we still alive
        # we have to send PONG to server for make it doesn't close the connection
        if msg.startswith('PING'):
            self.event_loop.create_task(self.send('PONG :tmi.twitch.tv'))
            return
        # parse the message we got into tags, command and text
        tags, command, text = await self.parse_message(msg)
        # some system info will have integer as command-type, so skipping it
        if is_int(command[1]):
            return

        # messages from users in a channel will contains 'PRIVMSG'
        elif command[1] == 'PRIVMSG':
            # print('!-!-!-We GOT message with:\n',
            # 'tags = ', tags, '\n'
            # 'command = ', command, '\n'
            # 'text = ', text)
            channel_id = int(tags['room-id'])
            channel = self.joined[channel_id]
            author = Member(channel, tags)
            message = Message(channel, author, text, tags)
            print(message)


        # i don't get when we're getting that, but have to have
        elif command[1] == 'USERSTATE':
            pass
        
        # When some one JOIN a channel that we check
        elif command[1] == 'JOIN':
            pass

        # When some one LEFT a channel that we check
        elif command[1] == 'PART':
            pass

        # or we get info about channel we joined, or about updates in that channel
        elif command[1] == 'ROOMSTATE':
            # if we get 7 tags, it's info
            id = int(tags['room-id'])
            if len(tags) == 7:
                self.joined[id] = Channel(command[2][1:], self.ws, tags)
                print('----GOT NEW CHANNEL', self.joined[id].name)
                if self.on_room_join:
                    self.event_loop.create_task(self.on_room_join(self.joined[id]))
            # if we get 2 tags, it's update of room
            elif len(tags) == 2:
                if self.on_room_update != None:
                    before = copy(self.joined[id])
                    self.joined[id].update(tags)
                    self.event_loop.create_task(self.on_room_update(before, self.joined[id]))
                else:
                    self.joined[id].update(tags)
            return

        # 'GLOBALUSERSTATE' means it's message with info about us( about our bot )
        elif command[1] == 'GLOBALUSERSTATE':
            self.color = tags['color']
            self.nick = tags['display-name']
            self.emotes = tuple(map( int, tags['emote-sets'].split(',') ))
            self.id = int(tags['user-id'])
            self.badges = Member.badges_to_dict(tags['badges'])
            self.badges_info = Member.badges_to_dict(tags['badge-info'])
            if self.on_login != None:
                self.event_loop.create_task(
                    self.on_login(self.id, self.nick, self.emotes, \
                                  self.color, self.badges, self.badges_info))
            return

        print('!!!Found nothing!!!')
        

    async def parse_message(self, msg: str):
        tags = None # just objects to return
        command = None
        text = None
        
        # we may don't get tags, if so we won't have space before colon
        if msg.startswith(':'):
            parts = msg.split(':', 2)
        # if we get tags, they startwith '@', so we have to split by ' :'
        # because tags can contain ':' but can't contain ' :' (space+colon)
        elif msg.startswith('@'):
            parts = msg.split(' :', 2)
        # create dict of tags {<tag_name>: <value>, ...}
        # if we got tags, we deleting '@' it in parts[0][1:]
        tags = self.prefix_to_dict(parts[0][1:])
        command = parts[1].split(' ')
        # we may don't recieve text, if so - text is None
        if len(parts) == 3:
            text = parts[2]

        return tags, command, text


    def prefix_to_dict(self, prefix: str):
        tags = {} # we'll return tags
        i = 0 # simple current index of <tag_name> searching
        last = 0 # position of end of last tag-value
        while i < len(prefix):
            # if we found '=' - all before is <tag_name>
            if prefix[i] == '=':
                key = prefix[last:i]
                j = i + 1 # simple current index of <tag_value> searching
                while j < len(prefix):
                    # if we found ';' - all between '='(i) and ';'(j) is value
                    if prefix[j] == ';':
                        value = prefix[i+1:j]
                        tags[key] = value
                        i = last = j + 1
                        break
                    j += 1
                # last tag has not ';' in end, so just take all
                else:
                    value = prefix[i+1:]
                    tags[key] = value
            i += 1
        return tags

