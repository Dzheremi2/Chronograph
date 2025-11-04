import contextlib
from pathlib import Path
from typing import Optional, Union

import httpx
from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.backend.asynchronous.async_task import AsyncTask
from chronograph.backend.file.library_model import LibraryModel
from chronograph.backend.lrclib.lrclib_service import FetchStates, LRClibService
from chronograph.backend.lrclib.responses import LRClibEntry
from chronograph.backend.lyrics.lyrics_file import LyricsFile
from chronograph.backend.media import BaseFile  # noqa: TC001
from chronograph.internal import Constants, Schema

gtc = Gtk.Template.Child


@Gtk.Template(
  resource_path=Constants.PREFIX + "/gtk/ui/dialogs/MassDownloadingDialog.ui"
)
class MassDownloadingDialog(Adw.Dialog):
  __gtype_name__ = "MassDownloadingDialog"

  fetch_log_list_box: Gtk.ListBox = gtc()
  no_log_yet: Adw.StatusPage = gtc()

  log_items: Gio.ListStore = GObject.Property(type=Gio.ListStore)

  _fetch_going = False

  def __init__(self) -> None:
    super().__init__()
    self.fetch_log_list_box.set_placeholder(self.no_log_yet)
    store = Gio.ListStore.new(item_type=LogEntry)
    self.set_property("log_items", store)
    self.fetch_log_list_box.bind_model(self.log_items, self._log_row_factory)
    self._task_cancel_hdl = None

  @Gtk.Template.Callback()
  def _on_fetch_button_clicked(self, button: Gtk.Button) -> None:
    def on_all_done(*_args) -> None:
      self._fetch_going = False
      button.set_label(_("Fetch"))

    if not self._fetch_going:
      if self.log_items.get_n_items() != 0:
        self.log_items.remove_all()
        # FIXME: Create a class (in dgutils) wrapper for Handlers to provide an API
        # methods "disconnect_all" to kill all handlers
        LRClibService().disconnect(self.fstr)
        LRClibService().disconnect(self.fmsg)
        LRClibService().disconnect(self.fst)
        LRClibService().disconnect(self.fad)
      if getattr(self, "_task_cancel_hdl", None) and getattr(self, "task", None):
        with contextlib.suppress(Exception):
          self.task.disconnect(self._task_cancel_hdl)
      self._task_cancel_hdl = None
      medias: list[BaseFile] = []
      for item in LibraryModel().library:
        media = item.get_child().model.mfile
        medias.append(media)
      self.task = AsyncTask(
        LRClibService().fetch_lyrics_many,
        medias,
        do_use_progress=True,
        do_use_cancellable=True,
      )
      self._task_cancel_hdl = self.task.connect("cancelled", self._on_task_cancelled)
      self.task.start()
      self._fetch_going = True
      self.fstr = LRClibService().connect(
        "fetch-started", lambda _lrclib, path: self.log_items.insert(0, LogEntry(path))
      )
      self.fmsg = LRClibService().connect("fetch-message", self._on_fetch_message)
      self.fst = LRClibService().connect("fetch-state", self._on_fetch_state)
      button.set_label(_("Cancel"))
      self.fad = LRClibService().connect("fetch-all-done", on_all_done)
    else:
      self.task.cancel()
      self._fetch_going = False
      button.set_label(_("Fetch"))

  def _on_fetch_state(
    self,
    _lrclib,
    path: str,
    state: FetchStates,
    entry: Optional[Union[LRClibEntry, Exception]],
  ) -> None:
    if entry is None:
      state = FetchStates.FAILED
    for item in self.log_items:
      if item.path == path:
        if isinstance(entry, Exception):
          state = FetchStates.FAILED
          match entry:
            case httpx.ConnectTimeout:
              item.props.message = _("Connection timed out")
            case httpx.ConnectError:
              item.props.message = _("Connection error occurred")
            case __:
              item.props.message = _("An error occurred: ") + str(entry)
        # fmt: off
        match state:
          case FetchStates.DONE:
            if entry.instrumental:
              item.props.instrumental = True
              item.props.message = _("Instrumental track. No lyrics available")
              return
            lyrics_file = LyricsFile(Path(path))
            dl_profile = Schema.get(
              "root.settings.general.mass-downloading.preferred-format"
            )
            match dl_profile:
              case "s":
                if entry.synced_lyrics.strip() != "":
                  lyrics_file.lrc_lyrics.text = entry.synced_lyrics
                  lyrics_file.lrc_lyrics.save()
                  item.props.done = True
                  return
                item.props.failed = True
                item.props.message = _("No synced lyrics found")
              case "s~p":
                if entry.synced_lyrics.strip() != "":
                  lyrics_file.lrc_lyrics.text = entry.synced_lyrics
                  lyrics_file.lrc_lyrics.save()
                  item.props.done = True
                elif entry.plain_lyrics.strip() != "":
                  lyrics_file.lrc_lyrics.text = entry.plain_lyrics
                  lyrics_file.lrc_lyrics.save()
                  item.props.done = True
                else:
                  item.props.failed = True
                  item.props.message = _("No lyrics found")
              case "p":
                if entry.plain_lyrics.strip() != "":
                  lyrics_file.lrc_lyrics.text = entry.plain_lyrics
                  lyrics_file.lrc_lyrics.save()
                  item.props.done = True
                  return
                item.props.failed = True
                item.props.message = _("No plain lyrics found")
          case FetchStates.FAILED: item.props.failed = True
          case FetchStates.CANCELLED: item.props.cancelled = True
        # fmt: on
        break

  def _on_fetch_message(self, _lrclib, path: str, message: str) -> None:
    for item in self.log_items:
      if item.path == path:
        item.set_property("message", message)
        break

  def _on_task_cancelled(self, *_args) -> None:
    for item in self.log_items:
      if not (
        item.props.done
        or item.props.failed
        or item.props.cancelled
        or item.props.instrumental,
      ):
        item.set_property("cancelled", True)
        item.set_property("message", _("Cancelled"))

  def _log_row_factory(self, item: "LogEntry") -> Adw.ActionRow:
    row = Adw.ActionRow(title=item.path, subtitle=item.message, use_markup=False)
    item.bind_property("message", row, "subtitle")
    prefix = Adw.Bin()
    spinner = Adw.Spinner()
    failed_icon = Gtk.Image(
      icon_name="chr-exclamation-mark-symbolic", css_classes=["error"]
    )
    done_icon = Gtk.Image(
      icon_name="chr-check-round-outline-symbolic", css_classes=["success"]
    )
    cancelled_icon = Gtk.Image(
      icon_name="nothing-found-symbolic", css_classes=["warning"]
    )
    instrumental_icon = Gtk.Image(
      icon_name="lrclib-track-symbolic", css_classes=["instrumental"]
    )
    prefix.set_child(spinner)
    row.add_prefix(prefix)
    item.connect("notify::failed", lambda *__: prefix.set_child(failed_icon))
    item.connect("notify::done", lambda *__: prefix.set_child(done_icon))
    item.connect("notify::cancelled", lambda *__: prefix.set_child(cancelled_icon))
    item.connect(
      "notify::instrumental", lambda *__: prefix.set_child(instrumental_icon)
    )
    return row


class LogEntry(GObject.Object):
  message: str = GObject.Property(type=str, default="")
  failed: bool = GObject.Property(type=bool, default=False)
  done: bool = GObject.Property(type=bool, default=False)
  cancelled: bool = GObject.Property(type=bool, default=False)
  instrumental: bool = GObject.Property(type=bool, default=False)

  def __init__(self, path: str, message: str = _("Pending")) -> None:
    super().__init__(message=message)
    self.path = path
