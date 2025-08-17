from gi.repository import Adw, GObject, Gtk

from chronograph.internal import Constants
from chronograph.utils.wbw.models.word_model import WordModel

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/wbw/WordWidget.ui")
class WordWidget(Adw.Bin):
    __gtype_name__ = "WordWidget"

    sync_higlight_box: Gtk.Box = gtc()
    timestamp_label: Gtk.Label = gtc()
    word_label: Gtk.Label = gtc()

    def __init__(self, word: WordModel) -> None:
        super().__init__()
        self.word = word
        self.word.bind_property(
            "word", self.word_label, "label", GObject.BindingFlags.SYNC_CREATE
        )
        self.word.bind_property(
            "timestamp", self.timestamp_label, "label", GObject.BindingFlags.SYNC_CREATE
        )
        self._set_in_current_line(self.word, None)
        self._on_is_highlighted_changed(self.word, None)
        self.word.connect("notify::synced", self._on_synced_changed)
        self.word.connect("notify::active", self._set_in_current_line)
        self.word.connect("notify::highlighted", self._on_is_highlighted_changed)
        if self.word.time != -1:
            self.word.set_property("synced", True)

    def _on_synced_changed(self, obj: WordModel, _arg) -> None:
        is_synced = obj.synced
        if is_synced:
            self.word_label.add_css_class("synced-text")
            self.timestamp_label.add_css_class("synced-text")
            self.sync_higlight_box.add_css_class("synced-card")
        else:
            self.word_label.remove_css_class("synced-text")
            self.timestamp_label.remove_css_class("synced-text")
            self.sync_higlight_box.remove_css_class("synced-card")

    def _on_is_highlighted_changed(self, model: WordModel, _arg):
        if model.highlighted:
            self.sync_higlight_box.add_css_class("word-frame")
        else:
            self.sync_higlight_box.remove_css_class("word-frame")

    def _set_in_current_line(self, model: WordModel, _arg) -> None:
        if model.active:
            self.word_label.remove_css_class("dimmed")
            self.timestamp_label.remove_css_class("dimmed")
        else:
            self.word_label.add_css_class("dimmed")
            self.timestamp_label.add_css_class("dimmed")
