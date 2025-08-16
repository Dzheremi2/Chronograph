from gi.repository import Adw, Gtk

from chronograph.internal import Constants
from chronograph.utils.wbw.models.lyrics_model import LyricsModel

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/wbw/LyricsWidget.ui")
class LyricsWidget(Adw.Bin):
    __gtype_name__ = "LyricsWidget"

    first_line_box: Gtk.Box = gtc()
    second_line_box: Gtk.Box = gtc()
    third_line_box: Gtk.Box = gtc()

    def __init__(self, lyrics: LyricsModel) -> None:
        super().__init__()
        self.lyrics = lyrics
        self.second_line_box.append(self.lyrics[0].widget)
        try:
            self.third_line_box.append(self.lyrics[1].widget)
        except IndexError:
            pass

        self.lyrics.connect("cindex-changed", self._on_index_changed)

    def _clean_all_boxes(self) -> None:
        if self.first_line_box.get_first_child():
            self.first_line_box.remove(self.first_line_box.get_first_child())
        if self.second_line_box.get_first_child():
            self.second_line_box.remove(self.second_line_box.get_first_child())
        if self.third_line_box.get_first_child():
            self.third_line_box.remove(self.third_line_box.get_first_child())

    def _on_index_changed(self, lyrics_model: LyricsModel, _old, new: int) -> None:
        self._clean_all_boxes()
        try:
            prev = lyrics_model[new - 1].widget
            prev.add_css_class("dimmed")
            self.first_line_box.append(prev)
        except IndexError:
            pass

        curr = lyrics_model[new].widget
        curr.remove_css_class("dimmed")
        self.second_line_box.append(curr)

        try:
            nxt = lyrics_model[new + 1].widget
            nxt.add_css_class("dimmed")
            self.third_line_box.append(nxt)
        except IndexError:
            pass
