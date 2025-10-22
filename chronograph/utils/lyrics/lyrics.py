import contextlib
import re
from typing import Any, Optional, Union

from gi.repository import GObject

from chronograph.internal import Constants, Schema
from chronograph.utils.lyrics.lyrics_format import LyricsFormat
from chronograph.utils.wbw.token_parser import TokenParser
from chronograph.utils.wbw.tokens import WordToken


class LyricsHierarchyConversion(Exception):
  """Raised if target lyrics format is hierarchically higher than lyrics format itself.

  Hierarchy::

      ELRC -> LRC -> PLAIN
  """

  def __init__(
    self, message="Target format is hierarchically higher than the source lyrics."
  ) -> None:
    super().__init__(message)


class Lyrics(GObject.Object):
  """A lyrics representing class with useful methods.

  Parameters
  ----------
  text : str
      Text of lyrics

  Emits
  ----------
  format-changed : int
      Emitted when lyrics format is changed. The new format is passed as an argument.
  save-triggered : str
      Emitted when lyrics should be saved. The file content is passed as an argument.
  """

  __gtype_name__ = "Lyrics"
  __gsignals__ = {
    "format-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    "save-triggered": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
  }

  _TIMED_LINE_RE = re.compile(r"^(\[\d{2}:\d{2}\.\d{2,3}\])(\S)")
  _TAG_PAIR_RE = re.compile(r"\[(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?P<val>.*?)\]")
  _TIMESTAMP = re.compile(r"^\d{2}:\d{2}(?:\.\d{2,3})?$")
  _SPACER = "\u00a0"

  _meta: dict
  _text: str

  def __init__(self, text: str) -> None:
    super().__init__()
    self._meta = self._parse_meta(text)
    self._text = self._strip_meta(text)
    self._detect_format()

    Constants.APP.connect(
      "shutdown",
      lambda *__: self.emit("save-triggered", self._construct_file_text()),
    )

  def __bool__(self) -> bool:
    return bool(self._text.strip())

  @classmethod
  def from_tokens(cls, lines: tuple[tuple[WordToken, ...], ...]) -> "Lyrics":
    """Creates a new instance of `self` from `WordToken`s. Suitable only for eLRC

    Parameters
    ----------
    lines : tuple[tuple[WordToken, ...], ...]
        Lines of lyrics in format of tuple(lines) of tuples(words) of `WordToken`s

    Returns
    -------
    Lyrics
        A new instance of `self`
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

  def save(self) -> None:
    """Emit save-triggered signal to indicate that lyrics should be saved."""
    self.emit("save-triggered", self._construct_file_text())

  def set_tag(self, key: str, value: str) -> None:
    """Set a tag in lyrics metadata.

    Parameters
    ----------
    key : str
        Tag key
    value : str
        Tag value
    """
    if key.lower() == "length":
      value = self._convert_length(value)
    elif key.lower() == "offset":
      value = int(value)

    self._meta[key.lower()] = value

  def to_format(self, target: LyricsFormat) -> None:
    """Convert lyrics to a given format

    Parameters
    ----------
    target : LyricsFormat
        Target lyrics format

    Raises
    ------
    LyricsHierarchyConversion
        Raised if conversion is not possible e.g. LRC to eLRC
    """
    if self._format.value > target.value:
      raise LyricsHierarchyConversion(
        f"Cannot convert from {self._format.name} to {target.name}. "
        "Conversion is only possible down the hierarchy."
      )

    if self._format == target:
      return

    if self._format == LyricsFormat.LRC and target == LyricsFormat.PLAIN:
      self._text = self._to_plain()

    if self._format == LyricsFormat.ELRC:
      match target:
        case LyricsFormat.LRC:
          self._text = self._to_lrc()
        case LyricsFormat.PLAIN:
          self._text = self._to_plain_from_elrc()
    self._detect_format()

  def of_format(self, target: LyricsFormat) -> str:
    """Returns lyrics in a given format. Does not replace original lyrics

    Parameters
    ----------
    target : LyricsFormat
        Target lyrics format

    Returns
    -------
    str
        Converted lyrics

    Raises
    ------
    LyricsHierarchyConversion
        Raised if conversion is not possible e.g. LRC to eLRC
    """
    if target.value > self._format.value:
      raise LyricsHierarchyConversion(
        f"Cannot convert from {self._format.name} to {target.name}. "
        "Conversion is only possible down the hierarchy."
      )

    if target.value == self._format.value:
      return self._text

    if self._format == LyricsFormat.LRC and target == LyricsFormat.PLAIN:
      return self._to_plain()

    if self._format == LyricsFormat.ELRC:
      if target == LyricsFormat.LRC:
        return self._to_lrc()
      if target == LyricsFormat.PLAIN:
        return self._to_plain_from_elrc()

  def get_normalized_lines(self) -> list[str]:
    """Returns normalized lyrics with whitespaces after the timestamp"""
    return [self._TIMED_LINE_RE.sub(r"\1 \2", line) for line in self._text.splitlines()]

  def _to_plain_from_elrc(self) -> str:
    lrc_text = self._to_lrc()
    lyrics_obj = Lyrics(lrc_text)
    return lyrics_obj._to_plain()

  def _to_lrc(self) -> str:
    lines = TokenParser.parse_lines(self._text)
    out = []
    for line in lines:
      if line.timestamp:
        out.append(f"[{line.timestamp}] {line.text}".strip())
      else:
        out.append(line.text)
    return "\n".join(out)

  def _to_plain(self) -> str:
    pattern = r"\[.*?\]"
    plain_lines = [
      re.sub(pattern, "", line).strip() for line in self._text.splitlines()
    ]
    return "\n".join(plain_lines)

  def _convert_length(self, lenght: Union[str, int]) -> Union[str, int]:
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
    out: list = []

    for line in text.splitlines():
      line = line.strip()
      if self._TAG_PAIR_RE.match(line):
        continue
      out.append(line)
    return "\n".join(out).strip()

  def _construct_file_text(self) -> str:
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

  def _detect_format(self) -> None:
    if self._text != "":
      if re.search(
        r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]\s*<\d{2}:\d{2}(?:\.\d{2,3})?>",
        self._text,
      ):
        fmt = LyricsFormat.ELRC
      elif re.search(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]", self._text):
        fmt = LyricsFormat.LRC
      else:
        fmt = LyricsFormat.PLAIN
    else:
      fmt = LyricsFormat.NONE
    self._format = fmt
    self.emit("format-changed", fmt.value)

  @property
  def text(self) -> str:
    """Lyrics text"""
    return self._text

  @text.setter
  def text(self, new_text: str) -> None:
    self._text = new_text
    self._detect_format()

  @property
  def format(self) -> LyricsFormat:
    """Lyrics format"""
    return self._format

  @property
  def meta(self) -> dict[str, Any]:
    """LRC metainfo tags"""
    return self._meta

  @staticmethod
  def _pick_timestamp_str(token: WordToken) -> Optional[str]:
    if token.timestamp and Lyrics._TIMESTAMP.match(token.timestamp):
      return token.timestamp
    if token.time is not None and token.time >= 0:
      return Lyrics._format_timestamp_ms(
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
    return word.word == Lyrics._SPACER * 20
