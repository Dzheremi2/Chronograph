from typing import Iterator, Optional

from gi.repository import Gio, GObject

from chronograph.utils.wbw.models.line_model import LineModel
from chronograph.utils.wbw.models.word_model import WordModel
from chronograph.utils.wbw.token_parser import TokenParser
from chronograph.utils.wbw.tokens import WordToken


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
        for line in TokenParser.parse_lines(lyrics):
            model = LineModel(line)
            store.append(model)
        self.set_property("lines", store)

        self.widget = LyricsWidget(self)

    def set_current(self, index: int) -> None:
        if index == self.cindex:
            return

        if 0 <= self.cindex < self.lines.get_n_items():
            old_line = self[self.cindex]
            if hasattr(self, "_eol_handler"):
                try:
                    old_line.disconnect(self._eol_handler)
                except (TypeError, RuntimeError):
                    pass
            old_line.set_is_current_line(False)
            old_line.set_current(-1)

        if 0 <= index < self.lines.get_n_items():
            old = self.cindex
            self.set_property("cindex", index)
            self.emit("cindex-changed", old, index)

            new_line = self[self.cindex]
            new_line.set_is_current_line(True)

            if new_line.cindex == -1 and new_line.words.get_n_items() > 0:
                new_line.set_current(0)

            self._eol_handler = new_line.connect("end-of-line", self._on_eol)
        else:
            self.set_property("cindex", -1)

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
            if line.get_latest_unsynced() is not None:
                return line, self.lines.find(line)[1]
        return None

    def get_current_line(self) -> LineModel:
        return self[self.cindex]

    def get_current_word(self) -> WordModel:
        return self.get_current_line().get_current_word()

    def get_tokens(self) -> tuple[tuple[WordToken, ...], ...]:
        lines = []
        for line_model in self:
            line = []
            for word in line_model:
                line.append(word.restore_token())
            lines.append(line)
        return tuple(lines)

    def _on_eol(self, _obj, direction: bool) -> None:
        if direction:
            self.next()
        else:
            self.previous()

    def __iter__(self) -> Iterator[LineModel]:
        for i in range(self.lines.get_n_items()):
            yield self.lines.get_item(i)

    def __getitem__(self, index) -> LineModel:
        try:
            if (item := self.lines.get_item(index)) is not None:
                return item
        except (OverflowError, IndexError) as e:
            raise IndexError("List index out of range") from e
