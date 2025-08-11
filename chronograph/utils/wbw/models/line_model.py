from typing import Iterator

from gi.repository import GObject

from chronograph.utils.wbw.elrc_parser import eLRCParser
from chronograph.utils.wbw.tokens import LineToken


class LineModel(GObject.Object):
    __gtype_name__ = "LineModel"

    text = GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    line = GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    time = GObject.Property(type=int, default=-1)
    timestamp = GObject.Property(type=str, default="")

    def __init__(self, line: LineToken) -> "LineModel":
        try:
            ms = int(line)
        except TypeError:
            ms = -1

        super().__init__(
            text=line.text,
            line=line.line,
            time=ms,
            timestamp=line.timestamp or "",
        )
        self.words = eLRCParser.parse_words(line)

    def __iter__(self) -> Iterator:
        return iter(self.words)
