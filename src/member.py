from channel import Channel
class Member:
    def __init__(self, channel: Channel, tags: dict):
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
    
    async def whisper(self, message: str):
        await self.channel.send(f'/w {self.name} {message}')


    async def ban(self, reason: str =''):
        await self.channel.send(f'/ban {self.name} {reason}')


    async def timeout(self, seconds: int):
        await self.channel.send(f'/timeout {self.name} {seconds}')

    
    async def unban(self):
        await self.channel.send(f'/unban {self.name}')


    async def vip(self):
        await self.channel.send(f'/vip {self.name}')


    async def unvip(self):
        await self.channel.send(f'/unvip {self.name}')


    async def mod(self):
        await self.channel.send(f'/mod {self.name}')


    async def unmod(self):
        await self.channel.send(f'/unmod {self.name}')


    @staticmethod
    def badges_to_dict(badges: str):
        result = {}
        for badge in badges.split(','):
            if badge:
                key, value = badge.split('/', 1)
                result[key] = value
        return result