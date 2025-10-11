import re

from gi.repository import Adw, Gtk

from chronograph.internal import Constants


@Gtk.Template(
  resource_path=Constants.PREFIX + "/gtk/ui/dialogs/ResyncAllAlertDialog.ui"
)
class ResyncAllAlertDialog(Adw.AlertDialog):
  __gtype_name__ = "ResyncAllAlertDialog"

  ms_entry: Gtk.Entry = Gtk.Template.Child()
  ms_entry_regex = re.compile(r"^-?\d+$")

  def __init__(self, page) -> None:
    super().__init__()
    self.page = page
    self._on_ms_entry_changed(self.ms_entry)
    self.ms_entry.connect("activate", self._on_response, "resync")

  @Gtk.Template.Callback()
  def _on_ms_entry_changed(self, entry: Gtk.Entry) -> None:
    if self.ms_entry_regex.match(entry.get_text()):
      self.ms_entry.remove_css_class("error")
      self.set_response_enabled("resync", True)
    else:
      self.ms_entry.add_css_class("error")
      self.set_response_enabled("resync", False)

  @Gtk.Template.Callback()
  def _on_response(self, _alert_dialog, response: str) -> None:
    if response == "resync":
      if self.ms_entry_regex.match(self.ms_entry.get_text()):
        ms = self.ms_entry.get_text()
        backwards = False
        if ms.startswith("-"):
          backwards = True
        self.page.resync_all(int(ms.replace("-", "")), backwards)
        del self.page
        self.close()
