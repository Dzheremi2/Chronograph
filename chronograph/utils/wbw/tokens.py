"""Tokens for Line and Word"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WordToken:
    word: str
    time: Optional[int] = None
    timestamp: Optional[str] = None

    def __str__(self) -> str:
        return self.word

    def __int__(self) -> int:
        if self.time is not None:
            return self.time
        raise TypeError(
            f'The word "{self.word}" ({self}) does not have time. Unable to convert to integer'
        )


@dataclass
class LineToken:
    text: str
    line: str
    time: Optional[int] = None
    timestamp: Optional[str] = None

    def __str__(self) -> str:
        return self.line

    def __int__(self) -> int:
        if self.time is not None:
            return self.time
        raise TypeError(
            f'The line "{self.line}" ({self}) does not have time. Unable to convert to integer'
        )
