from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class LRClibEntry:
  id: int
  track_name: str
  artist_name: str
  album_name: str
  duration: int
  instrumental: bool
  plain_lyrics: str
  synced_lyrics: str


@dataclass
class LRClibResponse:
  response: Optional[Iterable[LRClibEntry]] = None
  code: Optional[int] = None
  name: Optional[str] = None
  message: Optional[str] = None


@dataclass
class LRClibChallenge:
  prefix: str
  target: str
