from abc import ABC
from typing import Dict

from utils import badges_to_dict


class StateABC(ABC):
    def __init__(self, tags: Dict[str, str]):
        self.badges = badges_to_dict(tags['badges'])
        self.badges_info = badges_to_dict(tags['badge-info'])
