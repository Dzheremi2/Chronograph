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

    def __init__(self, model: WordModel) -> "WordWidget":
        super().__init__()
        self.model = model
        self.model.bind_property(
            "word", self.word_label, "label", GObject.BindingFlags.SYNC_CREATE
        )
        self.model.bind_property(
            "timestamp", self.timestamp_label, "label", GObject.BindingFlags.SYNC_CREATE
        )
        self.model.connect("notify::synced", self._on_synced_changed)

    def _on_synced_changed(self, obj: WordModel) -> None:
        is_synced = obj.synced
        if is_synced:
            self.word_label.add_css_class("synced-text")
            self.timestamp_label.add_css_class("synced-text")
            self.sync_higlight_box.add_css_class("synced-card")
        else:
            self.word_label.remove_css_class("synced-text")
            self.timestamp_label.remove_css_class("synced-text")
            self.sync_higlight_box.remove_css_class("synced-card")

    def set_highlighted(self, is_highlighted: bool) -> None:
        """Changes state of highlighting of `self` by adding or removing border

        Parameters
        ----------
        is_highlighted : bool
            Is border shown
        """
        if is_highlighted:
            self.sync_higlight_box.add_css_class("word-frame")
        else:
            self.sync_higlight_box.remove_css_class("word-frame")
