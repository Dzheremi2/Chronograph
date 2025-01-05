import pathlib

from gi.repository import Adw, Gtk  # type: ignore

from chronograph import shared


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/SyncLine.ui")
class SyncLine(Adw.EntryRow):
    """Line with text input for syncing purposes"""

    __gtype_name__ = "SyncLine"

    def __init__(self):
        super().__init__()
        self.focus_controller = Gtk.EventControllerFocus()
        self.focus_controller.connect("enter", self.update_selected_row)
        self.add_controller(self.focus_controller)
        self.connect("changed", self.save_file_on_update)

    def update_selected_row(self, event: Gtk.EventControllerFocus) -> None:
        """Updates global selected line to `self`

        Parameters
        ----------
        event : Gtk.EventControllerFocus
            event to grab line from
        """
        shared.selected_line = event.get_widget()

    def save_file_on_update(self, *_args) -> None:
        """Saves lines from `chronograph.ChronographWindow.sync_lines` to file"""
        if shared.schema.get_boolean("auto-file-manipulation"):
            lyrics = ""
            for line in shared.win.sync_lines:
                lyrics = lyrics + (line.get_text() + "\n")
            lyrics = lyrics[:-1]
            if (dir := shared.state_schema.get_string("opened-dir")) != "None":
                file = open(
                    dir
                    + pathlib.Path(shared.win.loaded_card._file.path).stem
                    + shared.schema.get_string("auto-file-format"),
                    "w",
                )
                file.write(lyrics)
                file.close()
