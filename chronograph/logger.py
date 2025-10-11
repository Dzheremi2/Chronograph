import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from chronograph.internal import Constants, Schema

_LOGGER_INITIALIZED = False


# pylint: disable=global-statement
def init_logger() -> None:
  """Initialize application logger.

  Creates a rotating log handler that keeps up to five previous
  logs and installs global exception hooks so any uncaught
  exception is written to the log file and printed to the console.
  """
  global _LOGGER_INITIALIZED
  if _LOGGER_INITIALIZED:
    return

  log_dir = Constants.CACHE_DIR / "chronograph" / "logs"
  log_dir.mkdir(parents=True, exist_ok=True)
  log_file = log_dir / "chronograph.log"

  file_handler = RotatingFileHandler(
    log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
  )
  file_handler.doRollover()
  formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
  file_handler.setFormatter(formatter)

  console_handler = logging.StreamHandler(stream=sys.stderr)
  console_handler.setLevel(logging.ERROR)
  console_handler.setFormatter(formatter)

  log_level = (
    logging.DEBUG
    if Constants.APP_ID.endswith("Devel")
    or Schema.get("root.settings.general.debug-profile")
    else logging.INFO
  )

  app_logger = logging.getLogger("App")
  app_logger.setLevel(log_level)
  app_logger.addHandler(file_handler)
  app_logger.addHandler(console_handler)

  player_logger = logging.getLogger("GstPlayer")
  player_logger.setLevel(log_level)
  player_logger.addHandler(file_handler)
  player_logger.addHandler(console_handler)

  lrclib_logger = logging.getLogger("LRClib")
  lrclib_logger.setLevel(log_level)
  lrclib_logger.addHandler(file_handler)
  lrclib_logger.addHandler(console_handler)

  logging.captureWarnings(True)

  def handle_exception(exc_type, exc_value, exc_traceback):
    app_logger.error(
      "Unhandled exception",
      exc_info=(exc_type, exc_value, exc_traceback),
    )

  sys.excepthook = handle_exception

  if hasattr(threading, "excepthook"):

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
      handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = _thread_hook

  _LOGGER_INITIALIZED = True
