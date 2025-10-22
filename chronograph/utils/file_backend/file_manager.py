from pathlib import Path
from typing import Optional

from gi.repository import Gio, GLib, GObject

from chronograph.internal import Constants, Schema
from dgutils import GSingleton

logger = Constants.FILE_LOGGER


class FileManager(GObject.Object, metaclass=GSingleton):
  """Manager singleton object for handling directories monitoring

  Parameters
  ----------
  path : Optional[Path]
    An initial path for monitoring, optional

  Emits
  -----
  renamed : str, str
    Emitted when any directory entry is renamed. Passes new path and old path
  created : str
    Emitted when a new file is created in monitored directory. Passed path of the new file
  deleted : str
    Emitted when any file was deleted. Passed its path
  directory-removed : str
    Emitted when a monitored directory was removed. Passes path of the removed directory
  target-root-changed : str
    Emitted when the target root directory for monitoring was changed. Passes new root path
  """

  __gtype_name__ = "FileManager"
  __gsignals__ = {
    "renamed": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    "created": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    "deleted": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    "directory-removed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    "target-root-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
  }

  monitor_path: Optional[Path] = None
  monitors: dict[str, Gio.FileMonitor] = {}

  def __init__(self, path: Optional[Path] = None) -> None:
    super().__init__()
    if path is not None:
      self.monitor_path = path
      logger.debug("FileManager was set up with monitor set to '%s'", path)
      self._setup_monitor(self.monitor_path)

  def set_directory(self, directory: Optional[Path]) -> None:
    """Sets currently observed directory to a provided `Path` object

    Parameters
    ----------
    directory : Optional[Path]
      `Path` of an observed directory
    """
    if directory is not None and directory != self.monitor_path:
      self.kill_all_monitors()
      self.monitor_path = directory
      self._setup_monitor(directory)
      self.emit("target-root-changed", str(directory))
    elif directory is None:
      self.monitor_path = None
      self.kill_all_monitors()

  def _setup_monitor(self, path: Path) -> None:
    abs_path = str(path.absolute())
    if abs_path in self.monitors:
      return

    try:
      gfile = Gio.File.new_for_path(abs_path)
      monitor = gfile.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)

      monitor.connect("changed", self._on_dir_changed)
      self.monitors[abs_path] = monitor
      logger.info("Monitoring --> '%s'", abs_path)

      if Schema.get("root.settings.general.recursive-parsing.enabled"):
        do_follow_symlinks = Schema.get(
          "root.settings.general.recursive-parsing.follow-symlinks"
        )
        for entry in path.iterdir():
          if entry.is_dir(follow_symlinks=do_follow_symlinks):
            self._setup_monitor(entry)
    except GLib.Error:
      logger.exception("Error occured while trying to setup monitoring for '%s'", path)

  def _recursively_emit_created(self, directory: Path) -> None:
    try:
      for entry in directory.iterdir():
        if entry.is_dir():
          self._recursively_emit_created(entry)
        elif entry.is_file():
          self.emit("created", entry.absolute().as_posix())

    except Exception:
      logger.exception(
        "Error during recursive file scan for new directory '%s'", directory
      )

  def _on_dir_changed(
    self,
    _monitor: Gio.FileMonitor,
    gfile_changed: Gio.File,
    gfile_other: Gio.File,
    event_type: Gio.FileMonitorEvent,
  ) -> None:
    changed_path = gfile_changed.get_path()
    logger.debug("[EVENT:%s], Path: '%s'", event_type.value_nick.upper(), changed_path)

    follow_symlinks = Schema.get(
      "root.settings.general.recursive-parsing.follow-symlinks"
    )

    match event_type:
      case Gio.FileMonitorEvent.CREATED | Gio.FileMonitorEvent.MOVED_IN:
        if Path(changed_path).is_dir(follow_symlinks=follow_symlinks):
          logger.info(
            "--> New directory created. Starting monitoring '%s'", changed_path
          )
          self._setup_monitor(Path(changed_path))
          self._recursively_emit_created(Path(changed_path))
        else:
          self.emit("created", gfile_changed.get_path())

      case Gio.FileMonitorEvent.DELETED:
        real_path = str(Path(changed_path).absolute())
        if real_path in self.monitors:
          logger.info(
            "--> Monitored directory deleted. Stopping monitoring '%s'", real_path
          )
          self.monitors[real_path].cancel()
          del self.monitors[real_path]
        else:
          logger.info("--> Item '%s' was deleted", real_path)
          self.emit("deleted", real_path)

      case Gio.FileMonitorEvent.RENAMED:
        new_path = gfile_other.get_path()
        old_path = gfile_changed.get_path()
        logger.info("--> File '%s' was renamed to '%s'", old_path, new_path)
        self.emit("renamed", gfile_other.get_path(), gfile_changed.get_path())

        if Path(new_path).is_dir(follow_symlinks=follow_symlinks):
          old_abs_path = str(Path(old_path).absolute())
          if old_abs_path in self.monitors:
            self.monitors[old_abs_path].cancel()
            del self.monitors[old_abs_path]
            logger.info("--> Cleaned up monitor for old directory name: %s", old_path)
          self._setup_monitor(Path(new_path))
          self._recursively_emit_created(Path(new_path))

      case Gio.FileMonitorEvent.MOVED_OUT:
        # Gio for some reason don't pass the file destination path on this event for
        # trash moves. So treat all moves out as a deletion event
        logger.info("--> Item '%s' was moved out", changed_path)
        self.emit("deleted", changed_path)

        abs_changed_path = str(Path(changed_path).absolute())
        if abs_changed_path in self.monitors:
          self.emit("directory-removed", abs_changed_path)
          self.monitors[abs_changed_path].cancel()
          del self.monitors[abs_changed_path]
          logger.info(
            "--> Monitored directory deleted. Stopping monitoring '%s'",
            abs_changed_path,
          )

      case __:
        pass

  def kill_all_monitors(self) -> None:
    """Removes all monitors of monitored directories"""
    if not self.monitors:
      return

    logger.info("Killing %d monitors", len(self.monitors))

    for path_str, monitor in list(self.monitors.items()):
      try:
        monitor.cancel()
        logger.debug("Cancelled monitor for '%s'", path_str)
      except Exception:
        logger.exception("Error cancelling monitor %s", path_str)
    self.monitors.clear()
    logger.info("All monitors killed")
