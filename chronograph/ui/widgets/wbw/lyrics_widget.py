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
        self.first_line_box.append(self.lyrics[0].widget)
        self.second_line_box.append(self.lyrics[1].widget)
        self.third_line_box.append(self.lyrics[2].widget)
