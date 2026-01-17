from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ChronieTimings:
  """Timing data for a line or word (in milliseconds)."""

  start: Optional[int] = None
  end: Optional[int] = None

  def to_dict(self) -> Optional[dict[str, Optional[int]]]:
    """Serialize timings to a dictionary.

    Returns
    -------
    Optional[dict[str, Optional[int]]]
      Mapping with `start`/`end` or `None` if both are missing.
    """
    if self.start is None and self.end is None:
      return None
    return {"start": self.start, "end": self.end}

  @classmethod
  def from_dict(cls, data: Optional[dict[str, Any]]) -> Optional[ChronieTimings]:
    """Create timings from a dictionary.

    Parameters
    ----------
    data : Optional[dict[str, Any]]
      Mapping with `start` and/or `end` fields.

    Returns
    -------
    Optional[ChronieTimings]
      Parsed timings or `None` when no timing values are present.
    """
    if not isinstance(data, dict):
      return None
    start = _coerce_ms(data.get("start"))
    end = _coerce_ms(data.get("end"))
    if start is None and end is None:
      return None
    return cls(start=start, end=end)


@dataclass(frozen=True)
class ChronieWord:
  """A single word in a Chronie line."""

  word: str
  timings: Optional[ChronieTimings] = None

  def to_dict(self) -> dict[str, Any]:
    """Serialize the word into a dictionary.

    Returns
    -------
    dict[str, Any]
      Mapping with `word` and optional timing data.
    """
    return {
      "word": self.word,
      "timings": self.timings.to_dict() if self.timings else None,
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Optional[ChronieWord]:
    """Create a word entry from a dictionary.

    Parameters
    ----------
    data : dict[str, Any]
      Mapping with word text and optional timing data.

    Returns
    -------
    Optional[ChronieWord]
      Parsed word or `None` if input is invalid.
    """
    if not isinstance(data, dict):
      return None
    word = data.get("word")
    if word is None:
      return None
    timings = ChronieTimings.from_dict(data.get("timings"))
    return cls(str(word), timings)


@dataclass(frozen=True)
class ChronieLine:
  """A single Chronie line with optional per-line and per-word timings."""

  line: str
  timings: Optional[ChronieTimings] = None
  words: Optional[list[ChronieWord]] = None

  def to_dict(self) -> dict[str, Any]:
    """Serialize the line into a dictionary.

    Returns
    -------
    dict[str, Any]
      Mapping with line text, timings, and optional words.
    """
    return {
      "line": self.line,
      "timings": self.timings.to_dict() if self.timings else None,
      "words": [word.to_dict() for word in self.words] if self.words else None,
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Optional[ChronieLine]:
    """Create a line entry from a dictionary.

    Parameters
    ----------
    data : dict[str, Any]
      Mapping with line text, timings, and optional words.

    Returns
    -------
    Optional[ChronieLine]
      Parsed line or `None` if input is invalid.
    """
    if not isinstance(data, dict):
      return None
    line = data.get("line", "")
    timings = ChronieTimings.from_dict(data.get("timings"))
    words_raw = data.get("words")
    words = None
    if isinstance(words_raw, list):
      parsed_words = []
      for word_item in words_raw:
        word = ChronieWord.from_dict(word_item)
        if word is None:
          continue
        parsed_words.append(word)
      if parsed_words:
        words = parsed_words
    return cls(str(line), timings, words)


def _coerce_ms(value: Any) -> Optional[int]:
  if value is None:
    return None
  if isinstance(value, bool):
    return None
  try:
    return int(value)
  except (TypeError, ValueError):
    return None
