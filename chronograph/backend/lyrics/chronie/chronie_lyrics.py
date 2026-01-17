from __future__ import annotations

import json
from typing import Any, Optional

import yaml

from chronograph.backend.lyrics.chronie.data import ChronieLine
from chronograph.backend.lyrics.interfaces import LyricFormat


class ChronieLyrics(LyricFormat):
  """Chronograph internal lyrics format."""

  format = "chronie"

  def __init__(self, lines: Optional[list[ChronieLine]] = None) -> None:
    self.lines: list[ChronieLine] = list(lines or [])

  def __bool__(self) -> bool:
    return any(_line_has_text(line) for line in self.lines)

  def to_chronie(self) -> ChronieLyrics:
    return self

  @classmethod
  def from_chronie(cls, chronie: ChronieLyrics) -> ChronieLyrics:
    return chronie if isinstance(chronie, ChronieLyrics) else cls()

  def is_finished(self) -> bool:
    has_lines = False
    for line in self.lines:
      if not _line_has_text(line):
        continue
      has_lines = True
      line_timings = line.timings
      if line_timings is None or line_timings.start is None or line_timings.end is None:
        return False
      if not line.words:
        continue
      for word in line.words:
        if not word.word.strip():
          continue
        word_timings = word.timings
        if (
          word_timings is None or word_timings.start is None or word_timings.end is None
        ):
          return False
    return has_lines

  def is_lbl_finished(self) -> bool:
    """Check if all non-empty lines have a start timestamp.

    Returns
    -------
    bool
      `True` if line-by-line sync is complete.
    """
    has_lines = False
    for line in self.lines:
      if not _line_has_text(line):
        continue
      has_lines = True
      if not line.timings or line.timings.start is None:
        return False
    return has_lines

  def is_wbw_finished(self) -> bool:
    """Check if all non-empty words have a start timestamp.

    Returns
    -------
    bool
      `True` if word-by-word sync is complete.
    """
    has_words = False
    for line in self.lines:
      if not _line_has_text(line):
        continue
      if not line.words:
        return False
      for word in line.words:
        if not word.word.strip():
          continue
        has_words = True
        if not word.timings or word.timings.start is None:
          return False
    return has_words

  def exportable_formats(self) -> list[str]:
    """List available export formats for the current timing state.

    Returns
    -------
    list[str]
      Format names that can be exported from this Chronie data.
    """
    if not self:
      return []
    formats = ["plain"]
    if self.is_lbl_finished() or self.is_wbw_finished():
      formats.append("lrc")
    if self.is_wbw_finished():
      formats.append("elrc")
    return formats

  def to_dicts(self) -> list[dict[str, Any]]:
    """Serialize Chronie lines into Python dictionaries.

    Returns
    -------
    list[dict[str, Any]]
      List of line dictionaries.
    """
    return [line.to_dict() for line in self.lines]

  def to_json(self) -> str:
    """Serialize Chronie data into compact JSON.

    Returns
    -------
    str
      JSON string representation.
    """
    return json.dumps(self.to_dicts(), ensure_ascii=False, separators=(",", ":"))

  def to_file_text(self) -> str:
    return yaml.safe_dump(self.to_dicts(), sort_keys=False).strip()

  @classmethod
  def from_dicts(cls, data: Any) -> ChronieLyrics:
    """Create ChronieLyrics from parsed dictionaries.

    Parameters
    ----------
    data : Any
      Parsed Chronie list structure.

    Returns
    -------
    ChronieLyrics
      Parsed ChronieLyrics instance.
    """
    if not isinstance(data, list):
      raise TypeError("Chronie data must be a list")
    lines: list[ChronieLine] = []
    for item in data:
      line = ChronieLine.from_dict(item)
      if line is None:
        continue
      lines.append(line)
    return cls(lines)

  @classmethod
  def from_json(cls, text: str) -> ChronieLyrics:
    """Create ChronieLyrics from JSON text.

    Parameters
    ----------
    text : str
      JSON string representing Chronie data.

    Returns
    -------
    ChronieLyrics
      Parsed ChronieLyrics instance.
    """
    data = json.loads(text)
    return cls.from_dicts(data)

  @classmethod
  def from_yaml(cls, text: str) -> ChronieLyrics:
    """Create ChronieLyrics from YAML text.

    Parameters
    ----------
    text : str
      YAML string representing Chronie data.

    Returns
    -------
    ChronieLyrics
      Parsed ChronieLyrics instance.
    """
    data = yaml.safe_load(text) or []
    return cls.from_dicts(data)


def _line_has_text(line: ChronieLine) -> bool:
  if line.line.strip():
    return True
  if not line.words:
    return False
  return any(word.word.strip() for word in line.words)
