from gi.repository import Adw, Gtk

class SyncLine(Adw.EntryRow):
    """Line with text input for syncing purposes"""

    def update_selected_row(self, event: Gtk.EventControllerFocus) -> None: ...
    def save_file_on_update(self, *_args) -> None: ...
