from gi.repository import GObject, Gtk

from chronograph.internal import Constants

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/Bookmark.ui")
class Bookmark(Gtk.Box):
  __gtype_name__ = "Bookmark"

  title: Gtk.Label = gtc()

  def __init__(self, tag: str) -> None:
    self._tag = ""
    super().__init__()
    self._tag = tag
    self.title.set_label(tag)

  @GObject.Property(type=str, default="")
  def tag(self) -> str:
    return self._tag
