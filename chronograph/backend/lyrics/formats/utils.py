from typing import Optional

from chronograph.backend.lyrics.chronie import ChronieLine, ChronieTimings
from chronograph.backend.wbw.tokens import WordToken

SPACER = "\u00a0"


def format_timestamp_ms(ms: int, *, precise: bool = True) -> str:
  """Format milliseconds into an LRC-style timestamp.

  Parameters
  ----------
  ms : int
    Timestamp in milliseconds.
  precise : bool, optional
    Whether to use three-digit millisecond precision.

  Returns
  -------
  str
    Timestamp string in `MM:SS.xx` or `MM:SS.xxx` format.
  """
  m = ms // 60000
  s = (ms % 60000) // 1000
  sub = ms % 1000
  return (
    f"{m:02d}:{s:02d}.{sub:03d}"
    if precise
    else f"{m:02d}:{s:02d}.{str(sub).zfill(3)[:-1]}"
  )


def line_start_ms(line: ChronieLine) -> Optional[int]:
  """Get the first available start time for a Chronie line.

  Parameters
  ----------
  line : ChronieLine
    Line to inspect for start timings.

  Returns
  -------
  Optional[int]
    Line or first word start time in milliseconds.
  """
  if line.timings and line.timings.start is not None:
    return line.timings.start
  if not line.words:
    return None
  for word in line.words:
    if word.timings and word.timings.start is not None:
      return word.timings.start
  return None


def merge_timings(start: Optional[int], end: Optional[int]) -> Optional[ChronieTimings]:
  """Create a ChronieTimings object if any timing is present.

  Parameters
  ----------
  start : Optional[int]
    Start time in milliseconds.
  end : Optional[int]
    End time in milliseconds.

  Returns
  -------
  Optional[ChronieTimings]
    Timings object or `None` if both values are missing.
  """
  if start is None and end is None:
    return None
  return ChronieTimings(start=start, end=end)


def token_start_ms(token: WordToken) -> Optional[int]:
  """Normalize token start time, ignoring negative values.

  Parameters
  ----------
  token : WordToken
    Token to inspect.

  Returns
  -------
  Optional[int]
    Start time in milliseconds, or `None` if invalid.
  """
  if token.time is None:
    return None
  return token.time if token.time >= 0 else None


def is_spacer(word: WordToken) -> bool:
  """Check if a token represents a spacer sentinel.

  Parameters
  ----------
  word : WordToken
    Token to inspect.

  Returns
  -------
  bool
    `True` if the token is a spacer sentinel.
  """
  return word.word == SPACER * 20
