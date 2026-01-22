from pathlib import Path
from typing import Callable, Iterable

from gi.repository import Adw, Gtk

from chronograph.internal import Constants
from dgutils import Linker

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/ImportDialog.ui")
class ImportDialog(Adw.Dialog, Linker):
  __gtype_name__ = "ImportDialog"

  file_list_group: Adw.PreferencesGroup = gtc()
  import_with_lyrics_switch: Adw.ExpanderRow = gtc()
  elrc_prefix_entry: Adw.EntryRow = gtc()
  prefer_embedded_lyrics_switch: Adw.SwitchRow = gtc()
  move_files_switch: Adw.SwitchRow = gtc()
  import_button: Gtk.Button = gtc()

  def __init__(
    self, paths: Iterable[str], on_import: Callable[[list[str], bool, str, bool], None]
  ) -> None:
    super().__init__()
    Linker.__init__(self)
    self._on_import = on_import
    self._file_list = Gtk.StringList()

    for path in paths:
      if path:
        self._file_list.append(path)

    self.file_list_group.bind_model(self._file_list, self._row_factory)
    self.new_connection(self._file_list, "items-changed", self._on_items_changed)
    self.new_connection(self.import_button, "clicked", self._on_import_clicked)

    self.import_with_lyrics_switch.set_property("enable-expansion", True)
    self._on_items_changed(self._file_list, 0, 0, 0)
    self.new_connection(self, "closed", lambda *__: self.disconnect_all())

  def close(self) -> bool:
    self.disconnect_all()
    return super().close()

  def _row_factory(self, item: Gtk.StringObject) -> Gtk.Widget:
    path = item.get_string()
    row = Adw.ActionRow(
      title=Path(path).stem,
      subtitle=path,
      use_markup=False,
    )

    delete_button = Gtk.Button(icon_name="clean-files-symbolic")
    delete_button.add_css_class("destructive-action")
    delete_button.set_valign(Gtk.Align.CENTER)
    delete_button.connect("clicked", self._on_delete_clicked, item)

    suffix = Gtk.Box(valign=Gtk.Align.CENTER)
    suffix.append(delete_button)
    row.add_suffix(suffix)
    return row

  def _on_delete_clicked(self, _button, item: Gtk.StringObject) -> None:
    for idx in range(self._file_list.get_n_items()):
      if self._file_list.get_item(idx) is item:
        self._file_list.remove(idx)
        break

  def _on_items_changed(self, *_args) -> None:
    has_items = self._file_list.get_n_items() > 0
    self.import_button.set_sensitive(has_items)
    if not has_items:
      self.close()

  def _on_import_clicked(self, *_args) -> None:
    if self._file_list.get_n_items() == 0:
      return

    paths = [
      self._file_list.get_string(idx) for idx in range(self._file_list.get_n_items())
    ]
    import_with_lyrics = self.import_with_lyrics_switch.get_property("enable-expansion")
    elrc_prefix = self.elrc_prefix_entry.get_text().strip()
    prefer_embedded = self.prefer_embedded_lyrics_switch.get_active()
    move_files = self.move_files_switch.get_active()

    self.close()
    self._on_import(paths, import_with_lyrics, elrc_prefix, prefer_embedded, move_files)