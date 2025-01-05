from gi.repository import Gio, Gtk, Adw, GLib  # type: ignore

from chronograph import shared
from chronograph.utils.parsers import dir_parser, file_parser


def select_dir(*_args) -> None:
    """Creates `Gtk.FileDialog` to select directory for parsing by `chronograph.utils.parsers.dir_parser`"""
    dialog = Gtk.FileDialog(
        default_filter=Gtk.FileFilter(mime_types=["inode/directory"])
    )
    shared.win.open_source_button.set_child(Adw.Spinner())
    dialog.select_folder(shared.win, None, on_selected_dir)


def on_selected_dir(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
    """Callbacked by `select_dir`. Launching `chronograph.utils.parsers.dir_parser`

    Parameters
    ----------
    file_dialog : Gtk.FileDialog
        FileDialog, callbacked from `select_dir`
    result : Gio.Task
        Task for reading, callbacked from `select_dir`
    """
    try:
        dir = file_dialog.select_folder_finish(result)
        dir_parser(dir.get_path())
    except GLib.GError:
        shared.win.open_source_button.set_icon_name("open-source-symbolic")


def select_lyrics_file(*_args) -> None:
    """Creates `Gtk.FileDialog` to select file for parsing by `chronograph.utils.parsers.file_parser`"""
    dialog = Gtk.FileDialog(default_filter=Gtk.FileFilter(mime_types=["text/plain"]))
    dialog.open(shared.win, None, on_selected_lyrics_file)


def on_selected_lyrics_file(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
    """Callbacked by `select_lyrics_file`. Launches `chronograph.utils.parsers.file_parser` for selected file

    Parameters
    ----------
    file_dialog : Gtk.FileDialog
        FileDialog, callbacked from `select_lyrics_file`
    result : Gio.Task
        Task for reading, callbacked from `select_lyrics_file`
    """
    file = file_dialog.open_finish(result)
    file_parser(file.get_path())
