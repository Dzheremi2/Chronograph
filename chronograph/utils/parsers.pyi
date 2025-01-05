from typing import Union

from gi.repository import Gio, Gdk # type: ignore

from chronograph.utils.file_mutagen_id3 import FileID3
from chronograph.utils.file_mutagen_vorbis import FileVorbis

def dir_parser(path: str, *_args) -> None: ...
def songcard_idle(file: Union[FileID3, FileVorbis]) -> None: ...
def line_parser(string: str) -> str: ...
def timing_parser(string: str) -> int: ...
def clipboard_parser(*_args) -> None: ...
def on_clipboard_parsed(_clipboard, result: Gio.Task, clipboard: Gdk.Clipboard) -> None: ...
def file_parser(file: str) -> None: ...
def string_parser(string: str) -> None: ...
def sync_lines_parser() -> str: ...
