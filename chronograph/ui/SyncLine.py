import pathlib
import re

from gi.repository import Adw, Gtk  # type: ignore

from chronograph import shared


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/SyncLine.ui")
class SyncLine(Adw.EntryRow):
    """Line with text input for syncing purposes"""

    __gtype_name__ = "SyncLine"

    def __init__(self):
        super().__init__()
        self.text_field: Gtk.Text = None
        self.focus_controller = Gtk.EventControllerFocus()
        self.focus_controller.connect("enter", self.update_selected_row)
        self.add_controller(self.focus_controller)

        for item in self.get_child():
            for _item in item:
                if type(text_field := _item) == Gtk.Text:
                    self.text_field = text_field
                    break
        self.text_field.connect("backspace", self.rm_line_on_backspace)

    @Gtk.Template.Callback()
    def add_line_on_enter(self, *_args) -> None:
        """Adds new line below `self` on Enter press"""
        shared.win.on_append_selected_line_action()
        childs = []
        for child in shared.win.sync_lines:
            childs.append(child)
        index = childs.index(self)
        shared.win.sync_lines.get_row_at_index(index + 1).grab_focus()

    def rm_line_on_backspace(self, text: Gtk.Text) -> None:
        """Removes `self` and focuses on previous line if Backspace pressed when `self.text` length is 0

        Parameters
        ----------
        text : Gtk.Text
            Gtk.Text to get text length from
        """
        if text.get_text_length() == 0:
            lines = []
            for line in shared.win.sync_lines:
                lines.append(line)
            index = lines.index(self)
            shared.win.sync_lines.remove(self)
            shared.win.sync_lines.get_row_at_index(index - 1).grab_focus()

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
            lyrics_list = []
            for line in shared.win.sync_lines:
                lyrics_list.append(line.get_text() + "\n")
            lyrics = "".join(lyrics_list)
            with open(
                pathlib.Path(shared.win.loaded_card._file.path).with_suffix(
                    shared.schema.get_string("auto-file-format")
                ),
                "r",
            ) as file:
                metatags_filterout = re.compile(r"^\[\w+:[^\]]+\]$")
                lyrics_unfiltered = file.read().splitlines()
                for line in lyrics_unfiltered[:]:
                    if not metatags_filterout.match(line):
                        lyrics_unfiltered.remove(line)
                _lyrics = "\n".join(lyrics_unfiltered)
                if _lyrics.strip():
                    lyrics = _lyrics + "\n" + lyrics
            with open(
                pathlib.Path(shared.win.loaded_card._file.path).with_suffix(
                    shared.schema.get_string("auto-file-format")
                ),
                "w",
            ) as file:
                file.write(lyrics)
