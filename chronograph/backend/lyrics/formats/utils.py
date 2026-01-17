from typing import Optional

from chronograph.backend.lyrics.chronie import ChronieLine, ChronieTimings
from chronograph.backend.wbw.tokens import WordToken

SPACER = "\u00a0"


def format_timestamp_ms(ms: int, *, precise: bool = True) -> str:
  m = ms // 60000
  s = (ms % 60000) // 1000
  sub = ms % 1000
  return (
    f"{m:02d}:{s:02d}.{sub:03d}"
    if precise
    else f"{m:02d}:{s:02d}.{str(sub).zfill(3)[:-1]}"
  )


def line_start_ms(line: ChronieLine) -> Optional[int]:
  if line.timings and line.timings.start is not None:
    return line.timings.start
  if not line.words:
    return None
  for word in line.words:
    if word.timings and word.timings.start is not None:
      return word.timings.start
  return None


def merge_timings(start: Optional[int], end: Optional[int]) -> Optional[ChronieTimings]:
  if start is None and end is None:
    return None
  return ChronieTimings(start=start, end=end)


def token_start_ms(token: WordToken) -> Optional[int]:
  if token.time is None:
    return None
  return token.time if token.time >= 0 else None


def is_spacer(word: WordToken) -> bool:
  return word.word == SPACER * 20
