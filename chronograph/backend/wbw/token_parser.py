import re
from pathlib import Path
from typing import Optional, Union

from chronograph.backend.wbw.tokens import LineToken, WordToken


class TokenParser:
  """Parser for text or paths to convert lyrics to tokens"""

  LINE_TIMESTAMP = re.compile(
    r"^\s*\[(?P<ts>(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{2,3}))?)\]\s*"
  )
  WORD_TIMESTAMP = re.compile(r"\s*<\d{2}:\d{2}(?:\.\d{2,3})?>\s*")
  TOKEN = re.compile(
    r"(?:<(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{2,3}))?>\s*)?(?P<word>[^\s<>]+)"
  )
  TIMESTAMP = re.compile(r"^\d{2}:\d{2}(?:\.\d{2,3})?$")

  _SPACER = "\u00a0"

  def __new__(cls, *args, **kwargs) -> None:
    raise TypeError(f"{cls.__name__} may not be implemented")

  @staticmethod
  def _ms_from_parts(m: str, s: str, ms: Optional[str]) -> int:
    whole_ms = 0 if ms is None else (int(ms) if len(ms) == 3 else int(ms) * 10)
    return (int(m) * 60 + int(s)) * 1000 + whole_ms

  @staticmethod
  def parse_lines(data: Union[Path, str]) -> tuple[LineToken, ...]:
    """Generates a tuple of Separate `LineToken`s dataclasses

    Parameters
    ----------
    data : Union[Path, str]
      Path to a file or a string with all lyrics

    Returns
    -------
    tuple[LineToken, ...]
      `LineToken`s dataclasses tuple
    """

    def _strip_all_timestamps(string: str) -> str:
      # remove leading timestamp
      string = TokenParser.LINE_TIMESTAMP.sub("", string, count=1)
      # remove all per-word timestamps
      string = TokenParser.WORD_TIMESTAMP.sub(" ", string)
      # normalize whitespaces
      return " ".join(string.split())

    if isinstance(data, Path):
      lines = data.read_text(encoding="utf-8").splitlines()
    else:
      lines = data.splitlines()
    out: list[LineToken] = []

    for raw_line in lines:
      line = raw_line
      match = TokenParser.LINE_TIMESTAMP.match(raw_line)

      if match:
        timestamp_str: str = match.group("ts")
        time_ms: int = TokenParser._ms_from_parts(
          match.group("m"), match.group("s"), match.group("ms")
        )
        cleaned_text: str = _strip_all_timestamps(raw_line)
        out.append(LineToken(cleaned_text, line, time=time_ms, timestamp=timestamp_str))
      else:
        cleaned_text: str = _strip_all_timestamps(raw_line)
        out.append(LineToken(cleaned_text, line))
    return tuple(out)

  @staticmethod
  def parse_words(line: Union[LineToken, str]) -> tuple[WordToken, ...]:
    """Generates a tuple of `WordToken`s dataclasses

    Parameters
    ----------
    line : Union[LineToken, str]
      A line to parse

    Returns
    -------
    tuple[WordToken, ...]
      Tuple of `WordToken` dataclasses
    """
    raw = line.line if hasattr(line, "line") else line
    pos = 0
    match = TokenParser.LINE_TIMESTAMP.match(raw)
    if match:
      pos = match.end()

    tokens: list[WordToken] = []
    for token_match in TokenParser.TOKEN.finditer(raw, pos):
      token_match: re.Match[str]
      word = token_match.group("word")
      m, s, ms = (
        token_match.group("m"),
        token_match.group("s"),
        token_match.group("ms"),
      )
      if m is not None:
        timestamp_str = f"{m}:{s}.{ms}"
        total_ms = TokenParser._ms_from_parts(m, s, ms)
        tokens.append(WordToken(word, time=total_ms, timestamp=timestamp_str))
      else:
        tokens.append(WordToken(word))

    if not tokens:
      line_time: Optional[int] = None
      line_ts: Optional[str] = None
      if hasattr(line, "time"):
        try:
          line_time = int(line)
        except Exception:
          line_time = None
        line_ts = getattr(line, "timestamp", None) or None

      tokens.append(
        WordToken(TokenParser._SPACER * 20, time=line_time, timestamp=line_ts)
      )

    return tuple(tokens)
