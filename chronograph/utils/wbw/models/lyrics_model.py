from typing import Iterator

from gi.repository import Gio, GObject

from chronograph.utils.wbw.elrc_parser import eLRCParser
from chronograph.utils.wbw.models.line_model import LineModel


class LyricsModel(GObject.Object):
    __gtype_name__ = "LyricsModel"

    __gsignals__ = {
        "cindex_changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    lines: Gio.ListStore = GObject.Property(type=Gio.ListStore)
    cindex: int = GObject.Property(type=int, default=-1)
    position_ms: int = GObject.Property(type=int, default=-1)

    def __init__(self, lyrics: str) -> None:
        from chronograph.ui.widgets.wbw.lyrics_widget import LyricsWidget
        super().__init__()
        store: Gio.ListStore = Gio.ListStore.new(item_type=LineModel)
        for line in eLRCParser.parse_lines(lyrics):
            model = LineModel(line)
            store.append(model)
        self.set_property("lines", store)
        self.set_property("cindex", 0 if self.lines.get_n_items() > 0 else -1)

        self.widget = LyricsWidget(self)

    def set_current(self, index: int) -> None:
        if index == self.cindex:
            return
        if 0 <= index < self.lines.get_n_items():
            old = self.cindex
            self.set_property("cindex", index)
            self.emit("cindex_changed", old, index)

    def next(self) -> None:
        if self.cindex + 1 < self.lines.get_n_items():
            self.set_current(self.cindex + 1)

    def previous(self) -> None:
        if self.cindex - 1 >= 0:
            self.set_current(self.cindex - 1)

    def __iter__(self) -> Iterator:
        for i in range(self.lines.get_n_items()):
            yield self.lines.get_item(i)

    def __getitem__(self, index) -> LineModel:
        return self.lines.get_item(index)
