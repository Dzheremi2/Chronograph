from gi.repository import Gtk, Adw

class SavedLocation(Gtk.Box):
    """Saved location row for saves sidebar

    Parameters
    ----------
    path : str
        path/to/the/directory
    name : str
        name of the saved location, by default `os.path.basename(path)`
    """

    title: Gtk.Label
    actions_box: Gtk.Box
    self_action_button: Gtk.Button
    rename_popover: Gtk.Popover
    rename_entry: Adw.EntryRow

    path: str

    def perform_action(self, entry_row: Adw.EntryRow) -> None: ...
    def toggle_button(self, *_args) -> None: ...
    def remove_from_saves(self, *_args) -> None: ...
    def on_rename_save(self, entry_row: Adw.EntryRow) -> None: ...
