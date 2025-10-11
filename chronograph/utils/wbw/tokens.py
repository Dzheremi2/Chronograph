"""Tokens for Line and Word"""

from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class TokenBase:
  time: Optional[int] = None
  timestamp: Optional[str] = None

  def __int__(self) -> int:
    """Return token time if available.

    Raises
    ------
    TypeError
        If the token has no time specified
    """
    if self.time is not None:
      return self.time
    raise TypeError(
      f'The token "{self}" does not have time. Unable to convert to integer'
    )


@dataclass
class WordToken(TokenBase):
  """Token representing a single word."""

  word: str

  def __str__(self) -> str:
    """Return the word text."""
    return self.word


@dataclass
class LineToken(TokenBase):
  """Token representing a line."""

  text: str
  line: str

  def __str__(self) -> str:
    """Return the original line string."""
    return self.line
