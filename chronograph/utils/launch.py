from __future__ import annotations

import os
import sys
import urllib.parse
from typing import TYPE_CHECKING, Optional

from gi.repository import Gio

if TYPE_CHECKING:
  from pathlib import Path


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
  return Gio.AppInfo.launch_default_for_uri(uri)


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
  return _launch_uri(path.absolute().as_uri())
