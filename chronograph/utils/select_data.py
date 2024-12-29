import threading

from gi.repository import Gio, Gtk  # type: ignore

from chronograph import shared
from chronograph.utils.parsers import dir_parser, file_parser


def select_dir(*_args) -> None:
    """Creates `Gtk.FileDialog` to select directory for parsing by `chronograph.utils.parsers.dir_parser`"""
    dialog = Gtk.FileDialog(
        default_filter=Gtk.FileFilter(mime_types=["inode/directory"])
    )
    dialog.select_folder(shared.win, None, on_selected_dir)


def on_selected_dir(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
    """Callbacked by `select_dir`. Creates thread for `chronograph.utils.parsers.dir_parser` launches this function in it

    Parameters
    ----------
    file_dialog : Gtk.FileDialog
        FileDialog, callbacked from `select_dir`
    result : Gio.Task
        Task for reading, callbacked from `select_dir`
    """
    dir = file_dialog.select_folder_finish(result)
    thread = threading.Thread(target=lambda: (dir_parser(dir.get_path())))
    thread.daemon = True
    thread.start()


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