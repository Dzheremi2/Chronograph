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
      `None` if no lyric formats avaialble, `list[str]` of translated strings otherwise
    """
    for flag in value:
      if flag == AvailableLyrics.NONE:
        return None

    return [label for flag, label in _FLAG_LABELS.items() if value & flag]


_FLAG_LABELS = {
  AvailableLyrics.NONE: C_("means lyrics absence", "None"),
  AvailableLyrics.PLAIN: _("Plain"),
  AvailableLyrics.LRC: "LRC",
  AvailableLyrics.ELRC: "eLRC",
}

TEXT_LABELS = {"plain": _("Plain"), "lrc": "LRCL", "elrc": "eLRC"}
