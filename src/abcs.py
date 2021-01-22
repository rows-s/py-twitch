from abc import ABC
from typing import Dict

from utils import parse_raw_badges


class StateABC(ABC):
    def __init__(self, tags: Dict[str, str]):
        self.badges = parse_raw_badges(tags['badges'])
        self.badges_info = parse_raw_badges(tags['badge-info'])
