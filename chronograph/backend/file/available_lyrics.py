from gettext import pgettext as C_
from typing import Optional

from gi.repository import GObject


class AvailableLyrics(GObject.GFlags):
  """Flags for using in SongCardModel

  Using `this.to_strings(value)` get the list of translated names of available lyric
  formats for this SongCardModel
  """

  __gtype_name__ = "AvailableLyrics"

  NONE = 0
  PLAIN = 1 << 0
  LRC = 1 << 1
  ELRC = 1 << 2
  # TODO: To be extended

  @staticmethod
  def to_strings(value: "AvailableLyrics") -> Optional[list[str]]:
    """Returns a list of translated names of lyric formats depending on a given flags

    Parameters
    ----------
    value : AvailableLyrics
      Available lyrics in flags format

    Returns
    -------
    Optional[list[str]]
      `None` if no lyric formats available, `list[str]` of translated strings otherwise
    """
    for flag in value:
      if flag == AvailableLyrics.NONE:
        return None

    return [label for flag, label in _FLAG_LABELS.items() if value & flag]

  @staticmethod
  def from_formats(formats: list[str]) -> "AvailableLyrics":
    flags = AvailableLyrics.NONE
    for fmt in formats:
      flag = FORMAT_TO_FLAG.get(fmt.lower())
      if flag is not None:
        flags |= flag
    return flags


_FLAG_LABELS = {
  AvailableLyrics.NONE: C_("means lyrics absence", "None"),
  AvailableLyrics.PLAIN: _("Plain"),
  AvailableLyrics.LRC: "LRC",
  AvailableLyrics.ELRC: "eLRC",
}

FORMAT_TO_FLAG = {
  "plain": AvailableLyrics.PLAIN,
  "lrc": AvailableLyrics.LRC,
  "elrc": AvailableLyrics.ELRC,
}
FLAG_TO_FORMAT = {flag: fmt for fmt, flag in FORMAT_TO_FLAG.items()}

TEXT_LABELS = {"plain": _("Plain"), "lrc": "LRC", "elrc": "eLRC"}
