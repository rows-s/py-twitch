from channel import Channel
from member import Member

class Message:
    def __init__(self, channel: Channel, author: Member, content: str, tags: dict) -> None:
        self.channel = channel
        self.author = author
        self.content = content
        self.id = tags['id']
        self.emotes = {}
        self.time = int(tags['tmi-sent-ts'])
        self.is_replay = False
        self.parent = None
        self.emote_only: False
        self.flags = None

        for key in tags.keys():
            if key == 'emote_only':
                self.emote_only = True

            elif key == 'emotes':
                self.emotes = self.emotes_to_dict(tags[key])

            elif key == 'reply-parent-display-name':
                self.is_replay = True
                self.parent = ParentMessage(self.channel, tags)

            elif key == 'flags':
                self.flags = tags[key]

    async def delete(self) -> str:
        command = f'/delete {self.id}'
        await self.channel.send(command)
        return command
    
    @staticmethod
    def emotes_to_dict(emotes: str) -> dict:
        result = {} # to return
        # all emoted separated by '/'
        for emote in emotes.split('/'):
            # we can get empty str-'', if so return
            if not emote:
                return result
            # emote_id and emote_positions separated by ':'
            emote, positions = emote.split(':')
            poss = [] # final positions list
            # all pair of positions separated by ','
            positions = positions.split(',')
            # loop to handle all positions of current emote
            for pos in positions:
                # every positions looks like '2-4', so...
                first, last = pos.split('-')
                poss.append(int(first)) # append first position
                poss.append(int(last)) # append last position
                
            result[emote] = poss # insert emote_id & positions into result
        return result



    
class ParentMessage():
    def __init__(self, channel: Channel, tags: dict) -> None:
        self.channel = channel
        self.author_name = tags['reply-parent-user-login']
        self.author_id = int(tags['reply-parent-user-id'])
        self.content = self.replace(tags['reply-parent-msg-body'])
        self.id = tags['reply-parent-msg-id']

    async def delete(self) -> str:
        command = f'/delete {self.id}'
        await self.channel.send(command)
        return command

    # some parent content will contains ' ', '\', ';'
    # these will be repleced to        '\s','\\','\:'
    # in this function we replaceing all back
    @staticmethod
    def replace(text: str):
        text = list(text) # work with list will be easier
        i = 0 # simple current index
        while i < len(text):
            if text[i] == '\\': 
                if text[i+1] == 's': # if '\s' replace to ' '
                    text[i] = ' '
                    text.pop(i+1)
                elif text[i+1] == ':': # if '\:' replace to ';'
                    text[i] = ';'
                    text.pop(i+1)
                elif text[i+1] == '\\': # if '\\' replace to '\'
                    text.pop(i+1)
                # above we changing first letter and delete second
                # that's need to don't replace one letter twice
            i+=1
        return ''.join(text)