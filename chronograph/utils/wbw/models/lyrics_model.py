from typing import Iterator, Optional

from gi.repository import Gio, GObject

from chronograph.utils.wbw.elrc_parser import eLRCParser
from chronograph.utils.wbw.models.line_model import LineModel
from chronograph.utils.wbw.models.word_model import WordModel


class LyricsModel(GObject.Object):
    __gtype_name__ = "LyricsModel"

    __gsignals__ = {
        "cindex-changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    lines: Gio.ListStore = GObject.Property(type=Gio.ListStore)
    cindex: int = GObject.Property(type=int, default=-1)
    position_ms: int = GObject.Property(type=int, default=-1)

    _eol_handler: int

    def __init__(self, lyrics: str) -> None:
        from chronograph.ui.widgets.wbw.lyrics_widget import LyricsWidget

        super().__init__()
        store: Gio.ListStore = Gio.ListStore.new(item_type=LineModel)
        for line in eLRCParser.parse_lines(lyrics):
            model = LineModel(line)
            store.append(model)
        self.set_property("lines", store)

        self.widget = LyricsWidget(self)

    def set_current(self, index: int) -> None:
        if index == self.cindex:
            return
        if 0 <= index < self.lines.get_n_items():
            old = self.cindex
            self.set_property("cindex", index)
            self.emit("cindex-changed", old, index)
            print("cindex-changed", old, index)
            self._eol_handler = self[self.cindex].connect("end-of-line", self._on_eol)
        else:
            pass

    def next(self) -> None:
        if self.cindex + 1 < self.lines.get_n_items():
            self.set_current(self.cindex + 1)

    def previous(self) -> None:
        if self.cindex - 1 >= 0:
            self.set_current(self.cindex - 1)

    def get_latest_unsynced(self) -> Optional[tuple[LineModel, int]]:
        """Returns the last line and its index if not all of its words have been synchronized. `None` if all lines are synced

        Returns
        -------
        Optional[tuple[LineModel, int]]
        """

        for line in self:
            line: LineModel
            if line.get_latest_unsynced() is not None:
                return line, self.lines.find(line)[1]
        return None

    def get_current_line(self) -> LineModel:
        return self[self.cindex]

    def get_current_word(self) -> WordModel:
        return self.get_current_line().get_current_word()

    def _on_eol(self, _obj, direction: bool) -> None:
        if direction:
            self.next()
        else:
            self.previous()

    def __iter__(self) -> Iterator:
        for i in range(self.lines.get_n_items()):
            yield self.lines.get_item(i)

    def __getitem__(self, index) -> LineModel:
        try:
            if (item := self.lines.get_item(index)) is not None:
                return item
        except (OverflowError, IndexError) as e:
            raise IndexError("List index out of range") from e
