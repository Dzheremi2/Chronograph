from gi.repository import Adw, Gtk

from chronograph.internal import Constants
from dgutils import Linker

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/ImportingDialog.ui")
class ImportingDialog(Adw.Dialog, Linker):
  __gtype_name__ = "ImportingDialog"

  import_status_label: Gtk.Label = gtc()
  import_detail_label: Gtk.Label = gtc()
  import_progress_bar: Gtk.ProgressBar = gtc()

  def __init__(self, total: int) -> None:
    super().__init__()
    Linker.__init__(self)
    self._total = max(total, 1)
    self.set_progress(0.0, 0)

  def set_progress(self, progress: float, imported: int) -> None:
    clamped = max(0.0, min(1.0, progress))
    self.import_progress_bar.set_fraction(clamped)
    self.import_detail_label.set_text(
      _("Imported {}/{}").format(imported, self._total)
    )
