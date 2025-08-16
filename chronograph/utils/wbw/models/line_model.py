from typing import Iterator

from gi.repository import Gio, GObject

from chronograph.utils.wbw.elrc_parser import eLRCParser
from chronograph.utils.wbw.models.word_model import WordModel
from chronograph.utils.wbw.tokens import LineToken


class LineModel(GObject.Object):
    __gtype_name__ = "LineModel"

    text = GObject.Property(type=str, default="")
    line = GObject.Property(type=str, default="")
    time = GObject.Property(type=int, default=-1)
    timestamp = GObject.Property(type=str, default="")
    cindex: int = GObject.Property(type=int, default=-1)
    words = GObject.Property(type=Gio.ListStore)

    def __init__(self, line: LineToken) -> None:
        from chronograph.ui.widgets.wbw.line_widget import LineWidget

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

        self.widget = LineWidget(self)

    def set_current(self, index: int) -> None:
        if index == self.cindex:
            return
        if 0 <= index < self.words.get_n_items():
            self.set_property("cindex", index)
            for word in self:
                word.set_property("highlighted", False)
            self.words.get_item(self.cindex).set_property("highlighted", True)

    def next(self) -> None:
        if self.cindex + 1 < self.words.get_n_items():
            self.set_current(self.cindex + 1)
            self.words.get_item(self.cindex).set_property("highlighted", False)
            self.words.get_item(self.cindex + 1).set_property("highlighted", True)

    def previous(self) -> None:
        if self.cindex - 1 >= 0:
            self.set_current(self.cindex - 1)
            self.words.get_item(self.cindex).set_property("highlighted", False)
            self.words.get_item(self.cindex - 1).set_property("highlighted", True)
        else:
            for word in self:
                word.set_property("highlighted", False)

    def set_is_current_line(self, is_current_line: bool) -> None:
        """Applied to all words to mark them as "in current line" or not.

        Parameters
        ----------
        in_current_line : bool
            True if this line is current, False otherwise
        """
        for word in self:
            word.set_property("active", is_current_line)

    def __iter__(self) -> Iterator:
        for i in range(self.words.get_n_items()):
            yield self.words.get_item(i)
