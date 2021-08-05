from typing import Iterable, Tuple, Generator

__all__ = ('BaseEmote', 'SubEmote', 'Emote')


class BaseEmote:
    def __init__(self, id_: str, content: str):
        self.id: str = id_
        self.content: str = content

    def __str__(self):
        return f'emote {self.id} ({self.content})'


class SubEmote(BaseEmote):
    def __init__(self, id_: str, content: str, start, end):
        super(SubEmote, self).__init__(id_, content)
        self.start = start
        self.end = end

    @property
    def position(self):
        return self.start, self.end

    def __str__(self):
        return f'emote {self.id} ({self.content}) in position {self.position}'


class Emote(BaseEmote):
    def __init__(self, id_: str, content: str, positions: Iterable[Tuple[int, int]]):
        super(Emote, self).__init__(id_, content)
        self.positions: Tuple[Tuple[int, int], ...] = tuple(positions)

    @property
    def count(self):
        return len(self.positions)

    def __iter__(self) -> Generator[SubEmote, None, None]:
        for position in self.positions:
            yield SubEmote(self.id, self.content, *position)

    def __str__(self):
        return f'emotes {self.id} ({self.content}) in positions {self.positions}'
