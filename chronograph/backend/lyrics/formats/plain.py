from chronograph.backend.lyrics.chronie import ChronieLine, ChronieLyrics
from chronograph.backend.lyrics.interfaces import LyricFormat


class PlainLyrics(LyricFormat):
  format = "plain"

  def __init__(self, text: str = "") -> None:
    self._text = text or ""

  @property
  def text(self) -> str:
    return self._text

  def to_file_text(self) -> str:
    return self._text.strip()

  def to_chronie(self) -> ChronieLyrics:
    lines = [ChronieLine(line=line) for line in self._text.splitlines()]
    return ChronieLyrics(lines)

  @classmethod
  def from_chronie(cls, chronie: ChronieLyrics) -> "PlainLyrics":
    lines: list[str] = []
    for line in chronie.lines:
      if line.line:
        lines.append(line.line)
        continue
      if line.words:
        lines.append(" ".join(word.word for word in line.words))
      else:
        lines.append("")
    return cls("\n".join(lines))

  def is_finished(self) -> bool:
    return False
