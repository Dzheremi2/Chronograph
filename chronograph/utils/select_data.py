from gi.repository import Adw, Gio, GLib, Gtk  # type: ignore

from chronograph import shared
from chronograph.utils.parsers import dir_parser, file_parser, parse_files

mime_types = (
    "audio/mpeg",
    "audio/aac",
    "audio/ogg",
    "audio/x-vorbis+ogg",
    "audio/flac",
    "audio/vnd.wave",
    "audio/mp4",
)


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


def select_files(*_args) -> None:
    """Creates `Gtk.FileDialog` to select files"""
    dialog = Gtk.FileDialog(default_filter=Gtk.FileFilter(mime_types=mime_types))
    shared.win.open_source_button.set_child(Adw.Spinner())
    dialog.open_multiple(shared.win, None, on_select_files)


def on_select_files(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
    """Callbacked by `select_files`. Adds selected files to the library by calling `parsers.parse_files`

    Parameters
    ----------
    file_dialog : Gtk.FileDialog
        File dialog callbacked from `select_files`
    result : Gio.Task
        Task for reading files from, callbacked from `select_files`
    """
    from chronograph.window import WindowState

    try:
        if shared.win.state == WindowState.LOADED_DIR:
            shared.win.library.remove_all()
            shared.win.library_list.remove_all()
        files = []
        gio_files = file_dialog.open_multiple_finish(result)
        for file in gio_files:
            files.append(file.get_path())
        parse_files(files)
        shared.win.state = WindowState.LOADED_FILES
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
