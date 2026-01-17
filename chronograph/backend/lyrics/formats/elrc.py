import re
from typing import Any, Optional

from chronograph.backend.lyrics.chronie import (
  ChronieLine,
  ChronieLyrics,
  ChronieTimings,
  ChronieWord,
)
from chronograph.backend.lyrics.formats.common import (
  join_meta,
  normalize_lines,
  parse_meta,
  strip_meta,
)
from chronograph.backend.lyrics.formats.utils import (
  SPACER,
  format_timestamp_ms,
  is_spacer,
)
from chronograph.backend.lyrics.interfaces import LyricFormat
from chronograph.backend.wbw.token_parser import TokenParser
from chronograph.internal import Schema


class ElrcLyrics(LyricFormat):
  format = "elrc"

  _LINE_TIMESTAMP = re.compile(r"^\s*\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]\s*")
  _WORD_TOKEN = re.compile(
    r"(?:<(?P<ts>\d{1,2}:\d{2}(?:[.:]\d{1,3})?)>\s*)?(?P<word>[^\s<>]+)"
  )
  _TIMESTAMP = re.compile(r"^\d{2}:\d{2}(?:\.\d{2,3})?$")
  _SPACER = SPACER

  def __init__(self, text: str = "", meta: Optional[dict[str, Any]] = None) -> None:
    parsed_meta = parse_meta(text)
    if meta:
      parsed_meta.update(meta)
    self._meta = parsed_meta
    self._text = strip_meta(text)

  @property
  def text(self) -> str:
    return self._text

  def normalized_lines(self) -> list[str]:
    return normalize_lines(self._text)

  def to_file_text(self) -> str:
    return join_meta(self._text, self._meta)

  def to_chronie(self) -> ChronieLyrics:
    lines: list[ChronieLine] = []
    for line in TokenParser.parse_lines(self._text):
      word_tokens = [
        token for token in TokenParser.parse_words(line) if not is_spacer(token)
      ]
      words: Optional[list[ChronieWord]] = None
      if word_tokens:
        words = []
        for token in word_tokens:
          timings = (
            ChronieTimings(start=token.time, end=None)
            if token.time is not None
            else None
          )
          words.append(ChronieWord(token.word, timings))
      timings = (
        ChronieTimings(start=line.time, end=None) if line.time is not None else None
      )
      lines.append(ChronieLine(line=line.text, timings=timings, words=words))
    return ChronieLyrics(lines)

  @classmethod
  def from_chronie(cls, chronie: ChronieLyrics) -> "ElrcLyrics":
    out_lines: list[str] = []
    precise = Schema.get("root.settings.syncing.precise")

    for line in chronie.lines:
      line_timestamp = None
      if line.timings and line.timings.start is not None:
        line_timestamp = format_timestamp_ms(line.timings.start, precise=precise)

      words = line.words
      if not words and line.line:
        words = [ChronieWord(word) for word in line.line.split()]

      chunks: list[str] = []
      visible_count = 0
      for word in words or []:
        if not word.word:
          continue
        visible_count += 1
        timestamp = None
        if word.timings and word.timings.start is not None:
          timestamp = format_timestamp_ms(word.timings.start, precise=precise)
        if timestamp:
          chunks.append(f"<{timestamp}> {word.word}")
        else:
          chunks.append(word.word)

      if visible_count > 0:
        joined = " ".join(chunks)
        if line_timestamp:
          out_lines.append(f"[{line_timestamp}] " + joined)
        else:
          out_lines.append(joined)
      else:
        out_lines.append(f"[{line_timestamp}]" if line_timestamp else "")

    return cls("\n".join(out_lines))

  def is_finished(self) -> bool:
    if not self.text.strip():
      return False
    for raw_line in self._text.splitlines():
      line = raw_line.strip()
      if not line:
        continue
      line_has_timestamp = False
      match = self._LINE_TIMESTAMP.match(line)
      if match:
        line_has_timestamp = True
        line = line[match.end() :]

      tokens = list(self._WORD_TOKEN.finditer(line))
      if not tokens:
        if line_has_timestamp:
          continue
        return False

      for token in tokens:
        if token.group("word") and token.group("ts") is None:
          return False
    return True
