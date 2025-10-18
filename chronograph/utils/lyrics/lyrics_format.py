from enum import Enum
from gettext import pgettext as C_
from typing import Literal


class LyricsFormat(Enum):
  """Lyrics format enum

  ::

      NONE -> 0
      PLAIN -> 1
      LRC -> 2
      ELRC -> 3
  """

  NONE = 0
  PLAIN = 1
  LRC = 2
  ELRC = 3

  @classmethod
  def from_int(cls, member_id: Literal[0, 1, 2, 3]) -> "LyricsFormat":
    for member in cls:
      if member.value == member_id:
        return member
    raise TypeError(f"Provided ID of {member_id} is out of scope of LyricsFormat")

  @staticmethod
  def translate(member_id: Literal[0, 1, 2, 3]) -> str:
    # fmt: off
    match member_id:
      case 0: return C_("means lyrics absence", "None")
      case 1: return _("Plain")
      case 2: return "LRC"
      case 3: return "eLRC"
    # fmt: on
