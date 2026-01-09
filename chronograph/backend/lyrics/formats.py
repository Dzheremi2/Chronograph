import re
from typing import Optional

from chronograph.backend.lyrics.interfaces import (
  LyricsConversionError,
  StartLyrics,
)
from chronograph.backend.wbw.token_parser import TokenParser
from chronograph.backend.wbw.tokens import WordToken
from chronograph.internal import Schema

FORMAT_ORDER = {"plain": 1, "lrc": 2, "elrc": 3}
_ELRC_HINT = re.compile(
  r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]\s*<\d{2}:\d{2}(?:\.\d{2,3})?>"
)
_LRC_HINT = re.compile(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")


def detect_start_lyrics(text: str) -> StartLyrics:
  """Detect the most likely lyrics format from raw text.

  Parameters
  ----------
  text : str
    Raw lyrics text to inspect.

  Returns
  -------
  StartLyrics
    Instance matching detected format (plain, lrc, or elrc).
  """
  if _ELRC_HINT.search(text):
    return ElrcLyrics(text)
  if _LRC_HINT.search(text):
    return LrcLyrics(text)
  return PlainLyrics(text)


class PlainLyrics(StartLyrics):
  format = "plain"

  def as_format(self, target: str) -> str:
    """Convert plain lyrics to the requested format.

    Parameters
    ----------
    target : str
      Target format identifier.

    Returns
    -------
    str
      Converted lyrics text.

    Raises
    ------
    LyricsConversionError
      If conversion is unsupported.
    """
    target = target.lower()
    if target == "plain":
      return self.text
    raise LyricsConversionError(f"Cannot convert from {self.format} to {target}.")

  def is_finished(self) -> bool:
    """Return whether plain lyrics are considered fully synced.

    Returns
    -------
    bool
      Always False for plain lyrics.
    """
    return False


class LrcLyrics(StartLyrics):
  format = "lrc"
  _LINE_TIMESTAMP = re.compile(r"^\s*\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")

  def as_format(self, target: str) -> str:
    """Convert LRC lyrics to the requested format.

    Parameters
    ----------
    target : str
      Target format identifier.

    Returns
    -------
    str
      Converted lyrics text.

    Raises
    ------
    LyricsConversionError
      If conversion is unsupported.
    """
    target = target.lower()
    if target == "lrc":
      return self.text
    if target == "plain":
      return self._to_plain()
    raise LyricsConversionError(f"Cannot convert from {self.format} to {target}.")

  def is_finished(self) -> bool:
    """Check whether all lines have timestamps.

    Returns
    -------
    bool
      True if each non-empty line has a timestamp.
    """
    if not self.text.strip():
      return False
    for line in self._text.splitlines():
      if not line.strip():
        continue
      if not self._LINE_TIMESTAMP.search(line):
        return False
    return True


class ElrcLyrics(StartLyrics):
  format = "elrc"

  _LINE_TIMESTAMP = re.compile(r"^\s*\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]\s*")
  _WORD_TOKEN = re.compile(
    r"(?:<(?P<ts>\d{1,2}:\d{2}(?:[.:]\d{1,3})?)>\s*)?(?P<word>[^\s<>]+)"
  )
  _TIMESTAMP = re.compile(r"^\d{2}:\d{2}(?:\.\d{2,3})?$")
  _SPACER = "\u00a0"

  def as_format(self, target: str) -> str:
    """Convert eLRC lyrics to the requested format.

    Parameters
    ----------
    target : str
      Target format identifier.

    Returns
    -------
    str
      Converted lyrics text.

    Raises
    ------
    LyricsConversionError
      If conversion is unsupported.
    """
    target = target.lower()
    if target == "elrc":
      return self.text
    if target == "lrc":
      return self._to_lrc()
    if target == "plain":
      return LrcLyrics(self._to_lrc()).as_format("plain")
    raise LyricsConversionError(f"Cannot convert from {self.format} to {target}.")

  def is_finished(self) -> bool:
    """Check whether all words have timestamps.

    Returns
    -------
    bool
      True if every word token includes a timestamp.
    """
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

  def _to_lrc(self) -> str:
    lines = TokenParser.parse_lines(self._text)
    out = []
    for line in lines:
      if line.timestamp:
        out.append(f"[{line.timestamp}] {line.text}".strip())
      else:
        out.append(line.text)
    return "\n".join(out)

  @classmethod
  def from_tokens(cls, lines: tuple[tuple[WordToken, ...], ...]) -> "ElrcLyrics":
    """Build eLRC lyrics from word token lines.

    Parameters
    ----------
    lines : tuple[tuple[WordToken, ...], ...]
      Tokenized lines with timestamps and words.

    Returns
    -------
    ElrcLyrics
      Constructed lyrics instance.
    """
    out_lines: list[str] = []

    for line_tokens in lines:
      if not line_tokens:
        out_lines.append("")
        continue

      first = line_tokens[0]
      line_timestamp = cls._pick_timestamp_str(first)

      chunks: list[str] = []
      visible_count = 0
      for token in line_tokens:
        word = token.word
        if cls._is_spacer(token):
          continue
        visible_count += 1
        timestamp = cls._pick_timestamp_str(token)
        if timestamp:
          chunks.append(f"<{timestamp}> {word}")
        else:
          chunks.append(word)

      if visible_count > 0:
        if line_timestamp:
          out_lines.append(f"[{line_timestamp}] " + " ".join(chunks))
        else:
          out_lines.append(" ".join(chunks))
      else:
        out_lines.append(f"[{line_timestamp}]" if line_timestamp else "")

    return cls("\n".join(out_lines))

  @staticmethod
  def _pick_timestamp_str(token: WordToken) -> Optional[str]:
    if token.timestamp and ElrcLyrics._TIMESTAMP.match(token.timestamp):
      return token.timestamp
    if token.time is not None and token.time >= 0:
      return ElrcLyrics._format_timestamp_ms(
        token.time, precise=Schema.get("root.settings.syncing.precise")
      )
    return None

  @staticmethod
  def _format_timestamp_ms(ms: int, *, precise: bool = True) -> str:
    m = ms // 60000
    s = (ms % 60000) // 1000
    sub = ms % 1000
    return (
      f"{m:02d}:{s:02d}.{sub:03d}"
      if precise
      else f"{m:02d}:{s:02d}.{str(sub).zfill(3)[:-1]}"
    )

  @staticmethod
  def _is_spacer(word: WordToken) -> bool:
    return word.word == ElrcLyrics._SPACER * 20
