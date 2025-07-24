# pylint: disable=all

from pathlib import Path
from typing import Literal, TextIO

from gi.repository import Gdk, Gio, Gtk
from main import ChronographApplication
from window import ChronographWindow

class classproperty:
    def __init__(self, fget): ...
    def __get__(self, instance, owner): ...
    def __set__(self, instance, value): ...
    def setter(self, fset): ...

class Constants:
    """Shared variables and constants for the application"""

    APP_ID: str
    VERSION: str
    PREFIX: str
    CACHEV: int

    CFG_DIR: Path
    DATA_DIR: Path

    APP: ChronographApplication
    WIN: ChronographWindow

    COVER_PLACEHOLDER: Gdk.Texture

    CACHE_FILE: TextIO
    CACHE: dict

class Schema:
    """Schema for the application settings"""

    _instance: "Schema"

    STATELESS: Gio.Settings
    STATEFULL: Gio.Settings

    def __new__(cls) -> "Schema": ...
    @classmethod
    def bind(
        cls,
        schema: Literal["STATELESS", "STATEFULL"],
        key: str,
        target: Gtk.Widget,
        target_property: str,
        flags: Gio.SettingsBindFlags,
    ) -> None: ...

    ############### STATELESS values ###############
    @classproperty
    def auto_file_manipulation(cls) -> bool: ...
    @classproperty
    def auto_file_format(cls) -> str: ...
    @classproperty
    def reset_quick_editor(cls) -> bool: ...
    @classproperty
    def save_session(cls) -> bool: ...
    @classproperty
    def precise_milliseconds(cls) -> bool: ...
    @classproperty
    def auto_list_view(cls) -> bool: ...
    @classproperty
    def recursive_parsing(cls) -> bool: ...
    @classproperty
    def follow_symlinks(cls) -> bool: ...
    @classproperty
    def load_compressed_covers(cls) -> bool: ...
    @classproperty
    def compress_level(cls) -> int: ...
    @classproperty
    def default_format(cls) -> str: ...
    @classproperty
    def autosave_throttling(cls) -> int: ...

    ############### STATEFULL values ###############
    @classproperty
    def sorting(cls) -> str: ...
    @classproperty
    def view(cls) -> str: ...
    @classproperty
    def window_width(cls) -> int: ...
    @classproperty
    def window_height(cls) -> int: ...
    @classproperty
    def window_maximized(cls) -> bool: ...
    @classproperty
    def session(cls) -> str: ...
