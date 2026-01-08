import contextlib
import re
from abc import ABC, abstractmethod
from typing import Any, Optional


class LyricsError(Exception):
  """Base error for lyrics operations."""


class LyricsConversionError(LyricsError):
  """Raised when a lyrics format conversion is not possible."""


class LyricsBase(ABC):
  """Base lyrics interface."""

  format: str = ""

  def __init__(self, text: str = "", meta: Optional[dict[str, Any]] = None) -> None:
    self._meta = dict(meta or {})
    self._text = text or ""

  def __bool__(self) -> bool:
    return bool(self._text.strip())

  @property
  def text(self) -> str:
    return self._text

  @text.setter
  def text(self, value: str) -> None:
    self._text = value or ""

  @property
  def meta(self) -> dict[str, Any]:
    return dict(self._meta)

  @abstractmethod
  def as_format(self, target: str) -> str:
    """Return lyrics text in the requested format."""

  @abstractmethod
  def to_file_text(self) -> str:
    """Return file-compatible text for future export."""

  def is_finished(self) -> bool:
    """Return True when lyrics are fully synchronized."""
    return False


class StartLyrics(LyricsBase):
  """Lyrics formats that use only start tags (e.g., LRC/eLRC)."""

  _TIMED_LINE_RE = re.compile(r"^(\[\d{2}:\d{2}\.\d{2,3}\])(\S)")
  _TAG_PAIR_RE = re.compile(r"\[(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?P<val>.*?)\]")

  def __init__(self, text: str = "", meta: Optional[dict[str, Any]] = None) -> None:
    parsed_meta = self._parse_meta(text)
    if meta:
      parsed_meta.update(meta)
    super().__init__(self._strip_meta(text), parsed_meta)

  def normalized_lines(self) -> list[str]:
    """Return lines normalized with a space after timestamps."""
    return [self._TIMED_LINE_RE.sub(r"\1 \2", line) for line in self._text.splitlines()]

  def set_tag(self, key: str, value: str) -> None:
    """Set a tag in lyrics metadata."""
    if key.lower() == "length":
      value = self._convert_length(value)
    elif key.lower() == "offset":
      value = int(value)
    self._meta[key.lower()] = value

  def to_file_text(self) -> str:
    """Return file-compatible text for future export."""
    out_tags: list[str] = []
    for tag, val in self._meta.items():
      if tag == "length":
        str_length = self._convert_length(val)
        out_tags.append(f"[{tag}:{str_length}]")
        continue

      if tag == "offset":
        str_offset = f"+{val}" if val >= 0 else f"-{val}"
        out_tags.append(f"[{tag}:{str_offset}]")
        continue

      out_tags.append(f"[{tag}:{val}]")

    tags_str = "\n".join(out_tags)
    return (tags_str + "\n" + self._text).strip()

  def _to_plain(self) -> str:
    pattern = r"\[.*?\]"
    plain_lines = [
      re.sub(pattern, "", line).strip() for line in self._text.splitlines()
    ]
    return "\n".join(plain_lines)

  def _convert_length(self, lenght: str | int) -> str | int:
    if isinstance(lenght, str):
      lenght = lenght.strip()
      mm, ss = lenght.split(":")
      return (int(mm) * 60) + int(ss)

    if isinstance(lenght, int):
      mm, ss = divmod(lenght, 60)
      return f"{mm:02d}:{ss:02d}"

    raise TypeError("Only str and int are supported")

  def _parse_meta(self, text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for line in text.splitlines():
      for tag in self._TAG_PAIR_RE.finditer(line):
        key = tag.group("key").strip().lower()
        val = tag.group("val").strip()

        if key == "offset":
          with contextlib.suppress(ValueError):
            val = int(val)
        elif key == "length":
          with contextlib.suppress(ValueError):
            val = self._convert_length(val)

        out[key] = val

    return out

  def _strip_meta(self, text: str) -> str:
    out: list[str] = []

    for line in text.splitlines():
      line = line.strip()
      if self._TAG_PAIR_RE.match(line):
        continue
      out.append(line)
    return "\n".join(out).strip()


class EndLyrics(LyricsBase):
  """Lyrics formats that use start and end tags (e.g., SRT/ASS/TTML)."""

  def to_file_text(self) -> str:
    return self._text.strip()
