from abc import ABC
from channel import Channel
from member import Member
from utils import replace, emotes_to_dict, badges_to_dict
from typing import Dict, List


class UserEvent(ABC):
    def __init__(self,
                 author: Member,
                 channel: Channel,
                 tags: Dict[str, str],
                 content: str
                 ) -> None:

        self.author: Member = author
        self.channel: Channel = channel
        self.system_msg: str = replace(tags['system-msg'])
        self.emotes: Dict[str, List[int]] = emotes_to_dict(tags['emotes'])
        self.flags: str = tags['flags']
        self.id: str = tags['id']
        self.event_type: str = tags['msg-id']
        self.time: int = int(tags['tmi-sent-ts'])
        self.content = content


class State(ABC):
    def __init__(self, tags: Dict[str, str]):
        self.badges = badges_to_dict(tags['badges'])
        self.badges_info = badges_to_dict(tags['badge-info'])
