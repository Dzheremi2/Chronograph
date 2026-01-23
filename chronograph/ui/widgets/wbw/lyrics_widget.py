from gi.repository import Adw, Gtk

from chronograph.backend.wbw.models.lyrics_model import LyricsModel
from chronograph.internal import Constants
from dgutils.typing import unwrap

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/wbw/LyricsWidget.ui")
class LyricsWidget(Adw.Bin):
  __gtype_name__ = "LyricsWidget"

  first_line_box: Gtk.Box = gtc()
  second_line_box: Gtk.Box = gtc()
  third_line_box: Gtk.Box = gtc()

  def __init__(self, lyrics: LyricsModel) -> None:
    super().__init__()
    self.lyrics = lyrics
    self.lyrics.connect("cindex-changed", self._on_index_changed)

  def _clean_all_boxes(self) -> None:
    if self.first_line_box.get_first_child():
      self.first_line_box.remove(unwrap(self.first_line_box.get_first_child()))
    if self.second_line_box.get_first_child():
      self.second_line_box.remove(unwrap(self.second_line_box.get_first_child()))
    if self.third_line_box.get_first_child():
      self.third_line_box.remove(unwrap(self.third_line_box.get_first_child()))

  def _on_index_changed(self, lyrics_model: LyricsModel, _old, new: int) -> None:
    self._clean_all_boxes()
    try:
      prev = lyrics_model[new - 1].widget
      prev.line.set_is_current_line(False)
      self.first_line_box.append(prev)
    except IndexError:
      pass

    curr = lyrics_model[new].widget
    curr.line.set_is_current_line(True)
    self.second_line_box.append(curr)

    try:
      nxt = lyrics_model[new + 1].widget
      nxt.line.set_is_current_line(False)
      self.third_line_box.append(nxt)
    except (IndexError, AttributeError):
      pass
