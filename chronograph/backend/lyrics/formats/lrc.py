import re
from typing import Any, Optional

from chronograph.backend.lyrics.chronie import (
  ChronieLine,
  ChronieLyrics,
  ChronieTimings,
)
from chronograph.backend.lyrics.formats.common import (
  join_meta,
  normalize_lines,
  parse_meta,
  strip_meta,
)
from chronograph.backend.lyrics.formats.utils import format_timestamp_ms, line_start_ms
from chronograph.backend.lyrics.interfaces import LyricFormat
from chronograph.backend.wbw.token_parser import TokenParser
from chronograph.internal import Schema


class LrcLyrics(LyricFormat):
  format = "lrc"
  _LINE_TIMESTAMP = re.compile(r"^\s*\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")

  def __init__(self, text: str = "", meta: Optional[dict[str, Any]] = None) -> None:
    parsed_meta = parse_meta(text)
    if meta:
      parsed_meta.update(meta)
    self._meta = parsed_meta
    self._text = strip_meta(text)

  @property
  def text(self) -> str:
    """Return the raw LRC text without metadata tags.

    Returns
    -------
    str
      LRC lyrics text without meta tags.
    """
    return self._text

  def normalized_lines(self) -> list[str]:
    """Return LRC lines with normalized timestamp spacing.

    Returns
    -------
    list[str]
      Normalized lines.
    """
    return normalize_lines(self._text)

  def to_file_text(self) -> str:
    return join_meta(self._text, self._meta)

  def to_chronie(self) -> ChronieLyrics:
    lines: list[ChronieLine] = []
    for line in TokenParser.parse_lines(self._text):
      timings = (
        ChronieTimings(start=line.time, end=None) if line.time is not None else None
      )
      lines.append(ChronieLine(line=line.text, timings=timings, words=None))
    return ChronieLyrics(lines)

  @classmethod
  def from_chronie(cls, chronie: ChronieLyrics) -> "LrcLyrics":
    out_lines: list[str] = []
    precise = Schema.get("root.settings.syncing.precise")

    for line in chronie.lines:
      line_start = line_start_ms(line)
      if line_start is not None:
        timestamp = format_timestamp_ms(line_start, precise=precise)
        if line.line:
          out_lines.append(f"[{timestamp}] {line.line}".strip())
        else:
          out_lines.append(f"[{timestamp}]")
      else:
        out_lines.append(line.line)

    return cls("\n".join(out_lines))

  def is_finished(self) -> bool:
    if not self.text.strip():
      return False
    for line in self._text.splitlines():
      if not line.strip():
        continue
      if not self._LINE_TIMESTAMP.search(line):
        return False
    return True
