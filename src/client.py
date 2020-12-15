import asyncio

import websockets
from message import Message
from channel import *
from member import *
from copy import copy
from utils import is_int
from typing import Callable, Iterable, Union
from asyncio.coroutines import coroutine, iscoroutinefunction
from errors import FunctionIsNotCorutine, UnknownEvent

# our uri to connent to sever
uri = 'wss://irc-ws.chat.twitch.tv:443'

# class Client, it will create bots
class Client: 
    def __init__(self, token: str, login: str) -> None:
        self.token = token
        self.login = login
        self.channels = {} # dict of Channel-objects, id_channel: Channel
        self.channels_names = {} # dict of name_channel : id_channel
        self.ws = None
        self.event_loop = asyncio.get_event_loop()
        self.name = None
        self.color = None
        self.id = None
        self.emotes = None
        self.badges = {}
        self.badges_info = {}
        self.names = {}

    def run(self, channels: Iterable[str]) -> None:
        async def start():
            # creating websocket
            self.ws = await websockets.client.connect(uri, loop=self.event_loop)
            # asking server to capability
            await self.send('CAP REQ :twitch.tv/membership')
            await self.send('CAP REQ :twitch.tv/commands')
            await self.send('CAP REQ :twitch.tv/tags')
            # loging
            await self.send(f'PASS {self.token}')
            await self.send(f'NICK {self.login}')
            # joining the channels
            for channel in channels:
                await self.send(f'JOIN #{channel}')
            
            # loop to receive, split and handle messages we got
            while True:
                received_msgs = await self.ws.recv()
                for received_msg in received_msgs.split('\r\n'):
                    # sometimes we'll get more then 1 msg from server and
                    # if so - i like to create tasks and don't call them
                    # before we finish current loop
                    self.event_loop.create_task(self.handle_message(received_msg))
        # i don't know other way to start a event loop in function ;) So enjoy that
        self.event_loop.run_until_complete(start())


    async def handle_message(self, msg: str) -> None:
        # if we got empty msg - skip
        if len(msg) == 0:
            return
        print('>', msg)
        
        # sometimes (about once in 5 minutes) we'll receive PING
        # that means server is checking we still alive
        # we have to send PONG to server for make it doesn't close the connection
        if msg.startswith('PING'):
            self.to_do(self.send('PONG :tmi.twitch.tv'))
            return
        # parse the message we got into tags, command and text
        tags, command, text = await self.parse_message(msg)
        # some system info will have integer as command-type, so skipping it
        if is_int(command[1]):
            if command[1] == '353':
                name = command[4][1:] # channel name
                names = self.names.get(name)
                if names:
                    names.extend(text.split(' '))
                else:
                    self.names[name] = text.split(' ')
            if command[1] == '356':
                pass
        # messages from users in a channel will contains 'PRIVMSG'
        elif command[1] == 'PRIVMSG':
            if hasattr(self, 'on_message'):
                channel_id = int(tags['room-id'])
                channel = self.channels[channel_id]
                author = Member(channel, tags)
                message = Message(channel, author, text, tags)
                self.to_do(self.on_message(message))
            


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
            id = int(tags['room-id']) # id of channel
            if len(tags) == 7: # if we get 7 tags, it's info
                name = command[2][1:] # name of channel
                self.channels[id] = Channel(name, self.ws, tags) # create channel
                self.channels_names[name] = id # save pair of name_chnl : id_chnl
                if hasattr(self, 'on_room_join'): # if event is registered
                    self.to_do(self.on_room_join(self.channels[id]))
            
            elif len(tags) == 2: # if we get 2 tags, it's update of room
                # if event is registered
                if hasattr(self, 'on_room_update'): 
                    before = copy(self.channels[id]) # state of chnl before
                    self.channels[id].update(tags) # update the channel
                    after = copy(self.channels[id]) # state of chnl after
                    self.to_do(self.on_room_update(before, after)) # call event
                # else - insert updates and skip
                else:
                    self.channels[id].update(tags)
            return

        # 'GLOBALUSERSTATE' means it's message with info about us( about our bot )
        elif command[1] == 'GLOBALUSERSTATE':
            self.color = tags['color']
            self.name = tags['display-name']
            self.emotes = tuple(map( int, tags['emote-sets'].split(',') ))
            self.id = int(tags['user-id'])
            self.badges = Member.badges_to_dict(tags['badges'])
            self.badges_info = Member.badges_to_dict(tags['badge-info'])
            if hasattr(self, 'on_login'): # if even registered - call it
                self.to_do(self.on_login(self))
            return


    async def parse_message(self, msg: str) -> Iterable:
        tags = None # just objects to return
        command = None
        text = None
        
        # we may don't receive tags, if so we won't have space before colon
        if msg.startswith(':'):
            parts = msg.split(':', 2)
        # if we receive tags, they startwith '@', so we have to split by ' :'
        # because tags can contain ':' but can't contain ' :' (space+colon)
        elif msg.startswith('@'):
            parts = msg.split(' :', 2)
        # create dict = <tag_name>: <value>
        # if we received tags, we deleting '@' it in parts[0][1:]
        tags = self.prefix_to_dict(parts[0][1:])
        command = parts[1].split(' ')
        # we may don't receive text, if so - text is None
        if len(parts) == 3:
            text = parts[2]

        return tags, command, text


    async def send(self, command: str) -> str:
        await self.ws.send(command + '\r\n')
        return command


    async def send_msg(self, channel: str, text: str) -> str:
        command = f'PRIVMSG #{channel} :{text}'
        await self.send(command)
        return command

    def prefix_to_dict(self, prefix: str) -> dict:
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


    def event(self, coru: Callable) -> None:
        events = ('on_message', 'on_room_update', 'on_login', 'on_room_join')
        # func must be corutine ( use async def ...(): pass )
        if not iscoroutinefunction(coru):
            raise FunctionIsNotCorutine
        if coru.__name__ in (events):
            setattr(self, coru.__name__, coru)
        else:
            # what for a developer will register unknown event?
            # better tell him/her about
            raise UnknownEvent
    
    def to_do(self, coro):
        self.event_loop.create_task(coro)