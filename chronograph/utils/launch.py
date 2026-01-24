import os
import sys
from pathlib import Path
from typing import Union, cast

from gi.repository import Gio, GLib

from chronograph.internal import Constants

logger = Constants.LOGGER

_PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
_PORTAL_OBJ_PATH = "/org/freedesktop/portal/desktop"
_OPENURI_IFACE = "org.freedesktop.portal.OpenURI"


def _portal_openuri_proxy() -> Gio.DBusProxy:
  return Gio.DBusProxy.new_for_bus_sync(
    Gio.BusType.SESSION,
    Gio.DBusProxyFlags.NONE,
    None,
    _PORTAL_BUS_NAME,
    _PORTAL_OBJ_PATH,
    _OPENURI_IFACE,
    None,
  )


def _wait_portal_response(request_path: str) -> bool:
  bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
  done: dict[str, Union[bool, int]] = {"flag": False, "response": 2}

  def on_response(
    _conn, _sender, _obj_path, _iface, _signal, params: GLib.Variant
  ) -> None:
    response, _results = params.unpack()
    done["response"] = int(response)
    done["flag"] = True

  sub_id = bus.signal_subscribe(
    _PORTAL_BUS_NAME,
    "org.freedesktop.portal.Request",
    "Response",
    request_path,
    None,
    Gio.DBusSignalFlags.NONE,
    on_response,
  )

  ctx = GLib.MainContext.default()
  try:
    while not done["flag"]:
      ctx.iteration(True)
  finally:
    bus.signal_unsubscribe(sub_id)

  return done["response"] == 0


def _reveal_in_file_manager_portal(path: Path, parent_window: str = "") -> bool:
  proxy = _portal_openuri_proxy()

  flags = os.O_RDONLY
  if hasattr(os, "O_CLOEXEC"):
    flags |= os.O_CLOEXEC

  fd = os.open(str(path), flags)
  try:
    fd_list = Gio.UnixFDList.new()
    fd_index = fd_list.append(fd)

    options: dict[str, GLib.Variant] = {}
    params = GLib.Variant("(sha{sv})", (parent_window, fd_index, options))

    result, _out_fds = proxy.call_with_unix_fd_list_sync(
      "OpenDirectory",
      params,
      Gio.DBusCallFlags.NONE,
      -1,
      fd_list,
      None,
    )

    request_path = cast("str", result.unpack()[0])
    return _wait_portal_response(request_path)

  finally:
    os.close(fd)


def _launch_uri(uri: str) -> bool:
  if sys.platform == "win32":
    path = str(Path.from_uri(uri))
    if path:
      try:
        os.startfile(path)  # noqa: S606
        return True
      except OSError:
        return False
    return False

  if sys.platform == "linux":
    try:
      path = Path.from_uri(uri)
      ok = _reveal_in_file_manager_portal(path)
      if ok:
        return True

      # If the portal request was cancelled/failed, fallback to parent directory open.
      parent_dir_uri = path.parent.as_uri()
      return Gio.AppInfo.launch_default_for_uri(parent_dir_uri)

    except Exception:
      # Hard failure (no portal, D-Bus issues, etc.), fallback to opening parent directory.
      path = Path.from_uri(uri)
      parent_dir_uri = path.parent.as_uri()
      logger.exception(
        "Failed to reveal file via portal (%s). Falling back to opening parent directory.",
        path,
        stack_info=True,
      )
      return Gio.AppInfo.launch_default_for_uri(parent_dir_uri)

  return False


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

  if sys.platform == "win32":
    return _launch_uri(path.parent.absolute().as_uri())

  return False
