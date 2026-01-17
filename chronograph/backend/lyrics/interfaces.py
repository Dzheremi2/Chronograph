from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from chronograph.backend.lyrics.chronie import ChronieLyrics


class LyricsError(Exception):
  """Base error for lyrics operations."""


class LyricsConversionError(LyricsError):
  """Raised when a lyrics format conversion is not possible."""


class LyricFormat(ABC):
  """Abstract interface for lyric formats used for import/export."""

  format: str = ""

  @abstractmethod
  def to_chronie(self) -> ChronieLyrics:
    """Convert the format into Chronie lyrics.

    Returns
    -------
    ChronieLyrics
      Chronie representation of the lyrics.
    """

  @classmethod
  @abstractmethod
  def from_chronie(cls, chronie: ChronieLyrics) -> LyricFormat:
    """Build the format from Chronie lyrics.

    Parameters
    ----------
    chronie : ChronieLyrics
      Chronie lyrics to convert from.

    Returns
    -------
    LyricFormat
      New format instance.
    """

  @abstractmethod
  def is_finished(self) -> bool:
    """Return True if the lyrics are fully synchronized for this format.

    Returns
    -------
    bool
      `True` if the format has complete timing data.
    """

  @abstractmethod
  def to_file_text(self) -> str:
    """Return the lyrics in the format's file text representation.

    Returns
    -------
    str
      Lyrics serialized to the format's file representation.
    """
