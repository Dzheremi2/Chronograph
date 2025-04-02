from gi.repository import Adw, Gtk

path_str: str

class SavedLocation(Gtk.Box):
    """Saved location row for saves sidebar

    Parameters
    ----------
    path : str
        path/to/the/directory
    name : str
        name of the saved location, by default `os.path.basename(path)`
    """

    __gtype_name__: str

    title: Gtk.Label
    actions_popover: Gtk.Popover
    rename_popover: Gtk.Popover
    rename_entry: Adw.EntryRow
    deletion_alert_dialog: Adw.AlertDialog

    def __init__(self, path: str, name: str) -> None: ...
    def on_deletion_alert_response(
        self, _alert_dialog: Adw.AlertDialog, response: str
    ) -> None: ...
    def on_delete_save(self, *_args) -> None: ...
    def rename_save(self, *_args) -> None: ...
    def on_rename_entry_changed(self, text: Gtk.Text) -> None: ...
    def do_rename(self, entry_row: Adw.EntryRow) -> None: ...
    @property
    def path(self) -> str: ...
