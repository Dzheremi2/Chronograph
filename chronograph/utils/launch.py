import os
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

from gi.repository import Gio, GLib

from chronograph.internal import Constants

logger = Constants.LOGGER

if sys.platform == "linux":
  proxy = Gio.DBusProxy.new_for_bus_sync(
    Gio.BusType.SESSION,
    Gio.DBusProxyFlags.NONE,
    None,
    "org.freedesktop.FileManager1",
    "/org/freedesktop/FileManager1",
    "org.freedesktop.FileManager1",
    None,
  )


def _file_uri_to_path(uri: str) -> Optional[str]:
  if not uri.startswith("file://"):
    return None

  parsed = urllib.parse.urlparse(uri)
  path = urllib.parse.unquote(parsed.path)
  if parsed.netloc:
    path = f"//{parsed.netloc}{path}"
  if sys.platform == "win32" and path.startswith("/") and len(path) > 2:
    if path[2] == ":":
      path = path[1:]
  return path


def _launch_uri(uri: str) -> bool:
  if sys.platform == "win32":
    path = _file_uri_to_path(uri)
    if path:
      try:
        os.startfile(path)  # noqa: S606
        return True
      except OSError:
        return False
  if sys.platform == "linux":
    try:
      proxy.call_sync(
        "ShowItems",
        GLib.Variant("(ass)", [[uri], ""]),
        Gio.DBusCallFlags.NONE,
        -1,
        None,
      )
      return True
    except Exception:
      parent_dir_uri = Path.from_uri(uri).parent.as_uri()
      logger.exception(
        "Failed to launch file manager with file (%s) highlighted. Launched for parent directory",
        Path.from_uri(uri),
        stack_info=True,
      )
      return Gio.AppInfo.launch_default_for_uri(parent_dir_uri)


def launch_path(path: Path) -> bool:
  """Launch the default handler for a filesystem path.

  Parameters
  ----------
  path : Path
    Path to open with the system default application.

  Returns
  -------
  bool
    `True` if the launch request was accepted.
  """
  if sys.platform == "linux":
    return _launch_uri(path.absolute().as_uri())
  elif sys.platform == "win32":  # noqa: RET505
    return _launch_uri(path.parent.absolute().as_uri())
