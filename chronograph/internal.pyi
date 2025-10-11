# pylint: disable=all

from io import TextIOWrapper
from logging import Logger
from pathlib import Path
from typing import Final

from gi.repository import Gdk

from chronograph.main import ChronographApplication
from chronograph.window import ChronographWindow
from dgutils import Schema as Sch

class _Constants:
  APP_ID: Final[str]
  VERSION: Final[str]
  PREFIX: Final[str]
  CACHEV: Final[int]

  APP: Final[ChronographApplication]
  WIN: Final[ChronographWindow]
  CACHE_FILE: Final[TextIOWrapper]
  CACHE: dict

  CFG_DIR: Final[Path]
  DATA_DIR: Final[Path]
  CACHE_DIR: Final[Path]
  COVER_PLACEHOLDER: Final[Gdk.Texture]
  LOGGER: Logger
  PLAYER_LOGGER: Logger
  LRCLIB_LOGGER: Logger

Constants: _Constants
Schema: Sch
