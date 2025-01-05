import os

from gi.repository import Gdk, Gio, Gtk

from chronograph import shared


def export_clipboard(string: str) -> None:
    """Export passed string to user's clipboard

    Parameters
    ----------
    string : str
        string to export
    """
    clipboard = Gdk.Display.get_default().get_clipboard()
    clipboard.set(string)


def export_file(lyrics: str) -> None:
    """Requests user to select save destination

    Parameters
    ----------
    string : str
        string to save to file
    """
    dialog = Gtk.FileDialog(
        initial_name=os.path.basename(shared.win.loaded_card._file._path)
        + shared.schema.get_string("auto-file-format")
    )
    dialog.save(shared.win, None, on_export_file, lyrics)


def on_export_file(file_dialog: Gtk.FileDialog, result: Gio.Task, lyrics: str):
    """Saves string to file in selected destination

    Parameters
    ----------
    file_dialog : Gtk.FileDialog
        `Gtk.FileDialog` which returned destination
    result : Gio.Task
        Destination
    string : str
        string to save to file
    """
    filepath = file_dialog.save_finish(result).get_path()
    file = open(filepath, "w")
    file.write(lyrics)
    file.close()
