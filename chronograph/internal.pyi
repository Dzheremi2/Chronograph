from io import TextIOWrapper
from logging import Logger
from pathlib import Path
from typing import Final

from gi.repository import Gdk

from chronograph.main import ChronographApplication
from chronograph.window import ChronographWindow
from dgutils import Schema as Sch

class ConstantsMeta(type):
  @property
  def COVER_PLACEHOLDER(cls) -> Gdk.Texture: ...  # noqa: N802

class Constants(metaclass=ConstantsMeta):
  APP_ID: Final[str]
  VERSION: Final[str]
  PREFIX: Final[str]
  CACHEV: Final[int]
  DB_VER: Final[str]

  APP: Final[ChronographApplication]
  WIN: Final[ChronographWindow]
  CACHE_FILE: Final[TextIOWrapper]
  CACHE: dict

  CFG_DIR: Final[Path]
  DATA_DIR: Final[Path]
  CACHE_DIR: Final[Path]
  LOGGER: Logger
  PLAYER_LOGGER: Logger
  LRCLIB_LOGGER: Logger
  FILE_LOGGER: Logger
  DB_LOGGER: Logger

Schema: Sch
