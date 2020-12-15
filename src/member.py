from channel import Channel

class Member:
    def __init__(self, channel: Channel, tags: dict) -> None:
        self.channel = channel
        self.id = int(tags['user-id'])
        self.name = tags['display-name']
        self.color = None
        self.bits = 0
        self.subscriber = 0
        self.admin = False
        self.broadcaster = False
        self.mod = False
        self.client_nonce = None
        self.badges = {}
        self.badges_info = {}

        for key in tags.keys():
            if key == 'badges':
                self.badges = self.badges_to_dict(tags['badges'])
            elif key == 'badge-info':
                self.badges_info = self.badges_to_dict(tags['badge-info'])
            elif key == 'color':
                self.color = tags[key]
            elif key == 'client-nonce':
                self.client_nonce = tags[key]
        
        for badge in self.badges.keys():
            if badge == 'admin':
                self.admin = True
            elif badge == 'broadcaster':
                self.broadcaster = True
            elif badge == 'moderator':
                self.mod = True
            elif badge == 'bits':
                self.bits = int(self.badges[badge])
            elif badge == 'subscriber':
                self.subscriber = int(self.badges[badge])
    
    async def whisper(self, message: str) -> str:
        command = f'/w {self.name} {message}'
        await self.channel.send(command)
        return command


    async def ban(self, reason: str ='') -> str:
        command = f'/ban {self.name} {reason}'
        await self.channel.send(command)
        return command


    async def timeout(self, seconds: int) -> str:
        command = f'/timeout {self.name} {seconds}'
        await self.channel.send(command)
        return command

    
    async def unban(self) -> str:
        command = f'/unban {self.name}'
        await self.channel.send(command)
        return command


    async def vip(self) -> str:
        command = f'/vip {self.name}'
        await self.channel.send(command)
        return command


    async def unvip(self) -> str:
        command = f'/unvip {self.name}'
        await self.channel.send(command)
        return command


    async def mod(self) -> str:
        command = f'/mod {self.name}'
        await self.channel.send(command)
        return command


    async def unmod(self) -> str:
        command = f'/unmod {self.name}'
        await self.channel.send(command)
        return command


    @staticmethod
    def badges_to_dict(badges: str) -> dict:
        result = {} # to return
        # every bage/value separated by ','
        for badge in badges.split(','):
            # # we can get empety str, if so - skip
            if badge:
                # every bage & value separated by '/'
                key, value = badge.split('/', 1)
                result[key] = value
        return result