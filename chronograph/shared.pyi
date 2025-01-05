from pathlib import Path
from typing import TextIO

from gi.repository import Adw, Gio

from chronograph.main import ChronographApplication
from chronograph.window import ChronographWindow  # type: ignore

APP_ID: str
VERSION: str
PREFIX: str

config_dir: Path
data_dir: Path

schema: Gio.Settings
state_schema: Gio.Settings

app: ChronographApplication
win: ChronographWindow

selected_line: Adw.EntryRow
cache_file: TextIO
cache: dict