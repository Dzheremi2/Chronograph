from gi.repository import GObject

from chronograph.internal import Schema
from chronograph.utils.wbw.tokens import WordToken


class WordModel(GObject.Object):
    __gtype_name__ = "WordModel"

    word = GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    time = GObject.Property(type=int, default=-1)
    timestamp = GObject.Property(type=str, default="")
    synced = GObject.Property(type=bool, default=False)

    def __init__(self, word: WordToken) -> "WordModel":
        try:
            ms = int(word)
            synced = True
        except TypeError:
            ms = -1
            synced = False

        super().__init__(
            word=str(word),
            time=ms,
            timestamp=word.timestamp or "",
            synced=synced,
        )

        self.connect("notify::time", self._on_time_changed)

    def _on_time_changed(self, *_args) -> None:
        ms = self.time
        if ms < 0:
            self.set_property("timestamp", "")
            self.set_property("synced", False)
            return
        if Schema.get_precise_milliseconds():
            timestamp = f"{ms // 60000:02d}:{(ms % 60000)//1000:02d}.{ms % 1000:03d}"
        else:
            timestamp = f"{ms // 60000:02d}:{(ms % 60000)//1000:02d}.{(ms % 1000):03d}"[
                :-1
            ]
        self.set_property("timestamp", timestamp)
        self.set_property("synced", True)
