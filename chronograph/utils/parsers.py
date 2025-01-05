import os
import re
from pathlib import Path
from typing import Union

from gi.repository import Adw, Gdk, Gio, GLib  # type: ignore

from chronograph import shared
from chronograph.ui.SyncLine import SyncLine
from chronograph.utils.file_mutagen_id3 import FileID3
from chronograph.utils.file_mutagen_vorbis import FileVorbis


def dir_parser(path: str, *_args) -> None:
    """Parses directory and creates `SongCard` instances for files in directory of formats `ogg`, `flac`, `mp3` and `wav`

    Parameters
    ----------
    path : str
        Path to directory to parse
    """
    shared.win.library.remove_all()
    shared.win.open_source_button.set_child(Adw.Spinner())
    path = path + "/"
    mutagen_files = []
    for file in os.listdir(path):
        if not os.path.isdir(path + file):
            if Path(file).suffix in (".ogg", ".flac"):
                mutagen_files.append(FileVorbis(path + file))
            elif Path(file).suffix in (".mp3", ".wav"):
                mutagen_files.append(FileID3(path + file))

    for file in mutagen_files:
        GLib.idle_add(songcard_idle, file)

    shared.win.open_source_button.set_icon_name("open-source-symbolic")
    shared.win.library_scrolled_window.set_child(shared.win.library)
    shared.win.right_buttons_revealer.set_reveal_child(True)
    shared.win.left_buttons_revealer.set_reveal_child(True)
    shared.state_schema.set_string("opened-dir", path)
    # NOTE: This should be implemented in ALL parsers functions
    # for child in shared.win.library:
    #     child.set_focusable(False)


def songcard_idle(file: Union[FileID3, FileVorbis]) -> None:
    """Appends new `SongCard` instance to `ChronographWindow.library`

    Parameters
    ----------
    file : FileID3 | FileVorbis
        File of song
    """
    from chronograph.ui.SongCard import SongCard

    song_card = SongCard(file)
    shared.win.library.append(song_card)
    song_card.get_parent().set_focusable(False)


def line_parser(string: str) -> str:
    """Parses line for square brackets

    Parameters
    ----------
    string : str
        Line to parse

    Returns
    -------
    str
        Parsed string
    """
    pattern = r"\[([^\[\]]+)\]"
    try:
        return re.search(pattern, string)[0]
    except TypeError:
        return None


def timing_parser(string: str) -> int:
    """Parses string for timing in format `mm:ss.ms`

    Parameters
    ----------
    string : str
        String to parse

    Returns
    -------
    int
        Total milliseconds
    """
    try:
        pattern = r"(\d+):(\d+).(\d+)"
        mm, ss, ms = re.search(pattern, line_parser(string)).groups()
        total_ss = int(mm) * 60 + int(ss)
        total_ms = total_ss * 1000 + int(ms)
        return total_ms
    except TypeError:
        return None


def clipboard_parser(*_args) -> None:
    """Gets user clipboard for parsing"""
    clipboard = Gdk.Display().get_default().get_clipboard()
    clipboard.read_text_async(None, on_clipboard_parsed, user_data=clipboard)


def on_clipboard_parsed(_clipboard, result: Gio.Task, clipboard: Gdk.Clipboard) -> None:
    """Parses clipboard data and sets it to `ChronographWindow.sync_lines`

    Parameters
    ----------
    result : Gio.Task
        Task to get result from
    clipboard : Gdk.Clipboard
        Clipboard to read from
    """
    print()
    data = clipboard.read_text_finish(result)
    list = data.splitlines()
    shared.win.sync_lines.remove_all()
    for i in range(len(list)):
        shared.win.sync_lines.append(SyncLine())
        shared.win.sync_lines.get_row_at_index(i).set_text(list[i])


def file_parser(file: str) -> None:
    """Parses file and sets it to `chronograph.ChronographWindow.sync_lines`

    Parameters
    ----------
    file : str
        File to parse
    """
    file = open(file, "r")
    list = file.read().splitlines()
    childs = []
    for child in shared.win.sync_lines:
        childs.append(child)
    shared.win.sync_lines.remove_all()
    for i in range(len(list)):
        shared.win.sync_lines.append(SyncLine())
        shared.win.sync_lines.get_row_at_index(i).set_text(list[i])


def string_parser(string: str) -> None:
    """Sets `chronograph.ChronographWindow.sync_lines` with lyrics from provided string

    Parameters
    ----------
    string : str
        string to parse lyrics from
    """
    list = string.splitlines()
    shared.win.sync_lines.remove_all()
    for i in range(len(list)):
        shared.win.sync_lines.append(SyncLine())
        shared.win.sync_lines.get_row_at_index(i).set_text(list[i])


def sync_lines_parser() -> str:
    """Parses `chronograph.CronographWindow.sync_lines` for text, concatenates it and returns

    Returns
    -------
    str
        Parsed string

    Raises
    ------
    IndexError
        raised if not all lines have been synced
    """
    lyrics = ""
    for line in shared.win.sync_lines:
        if line_parser(line.get_text()) is not None:
            lyrics += line.get_text() + "\n"
        else:
            shared.win.toast_overlay.add_toast(
                Adw.Toast(title=_("Seems like not every line is synced"))
            )
            raise IndexError("Not all lines have timestamps")
    lyrics = lyrics[:-1]
    return lyrics
