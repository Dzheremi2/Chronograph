from typing import Iterator

from gi.repository import Gio, GObject

from chronograph.utils.wbw.elrc_parser import eLRCParser
from chronograph.utils.wbw.models.word_model import WordModel
from chronograph.utils.wbw.tokens import LineToken


class LineModel(GObject.Object):
    __gtype_name__ = "LineModel"

    __gsignals__ = {
        "cindex_changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    text = GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    line = GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    time = GObject.Property(type=int, default=-1)
    timestamp = GObject.Property(type=str, default="")
    cindex: int = GObject.Property(type=int, default=-1)
    words = GObject.Property(type=Gio.ListStore)

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

        store: Gio.ListStore = Gio.ListStore.new(item_type=WordModel)
        for word in eLRCParser.parse_words(line):
            model = WordModel(word)
            store.append(model)
        self.set_property("words", store)

    def set_current(self, index: int) -> None:
        if index == self.cindex:
            return
        if 0 <= index < self.words.get_n_items():
            old = self.cindex
            self.set_property("cindex", index)
            self.emit("cindex_changed", old, index)

    def next(self) -> None:
        if self.cindex + 1 < self.words.get_n_items():
            self.set_current(self.cindex + 1)

    def previous(self) -> None:
        if self.cindex - 1 >= 0:
            self.set_current(self.cindex - 1)

    def __iter__(self) -> Iterator:
        for i in range(self.words.get_n_items()):
            yield self.words.get_item(i)
