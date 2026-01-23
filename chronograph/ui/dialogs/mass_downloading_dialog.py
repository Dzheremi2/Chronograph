import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union, cast

import httpx
from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.backend.asynchronous.async_task import AsyncTask
from chronograph.backend.file.library_manager import LibraryManager
from chronograph.backend.file_parsers import parse_file
from chronograph.backend.lrclib.lrclib_service import FetchStates, LRClibService
from chronograph.backend.lrclib.responses import LRClibEntry
from chronograph.backend.lyrics import (
  chronie_from_text,
  get_track_lyric,
  save_track_lyric,
)
from chronograph.backend.media import BaseFile  # noqa: TC001
from chronograph.internal import Constants, Schema
from dgutils import Linker
from dgutils.typing import unwrap

if TYPE_CHECKING:
  from gi.repository.Gio import ListStore

  from chronograph.backend.file import SongCardModel

gtc = Gtk.Template.Child


@Gtk.Template(
  resource_path=Constants.PREFIX + "/gtk/ui/dialogs/MassDownloadingDialog.ui"
)
class MassDownloadingDialog(Adw.Dialog, Linker):
  __gtype_name__ = "MassDownloadingDialog"

  no_log_yet: Adw.StatusPage = gtc()
  already_fetched: Adw.StatusPage = gtc()

  progress_revealer: Gtk.Revealer = gtc()
  progress_bar: Gtk.ProgressBar = gtc()
  fetch_log_list_box: Gtk.ListBox = gtc()
  rewrite_already_existing_switch: Adw.SwitchRow = gtc()
  fetch_button: Gtk.Button = gtc()

  log_items: Gio.ListStore = cast("ListStore", GObject.Property(type=Gio.ListStore))

  _fetch_going = False

  def __init__(self) -> None:
    super().__init__()
    Linker.__init__(self)
    self.fetch_log_list_box.set_placeholder(self.no_log_yet)
    store = Gio.ListStore.new(item_type=LogEntry)
    self.set_property("log_items", store)
    self.fetch_log_list_box.bind_model(self.log_items, self._log_row_factory)
    self._task_cancel_hdl = None

    if Constants.WIN.state.value in (0, 1):
      self.fetch_button.set_sensitive(False)

    self.new_connection(
      Constants.WIN,
      "notify::state",
      lambda *__: self.fetch_button.set_sensitive(False)
      if Constants.WIN.state.value in (0, 1)
      else self.fetch_button.set_sensitive(True),
    )
    self.new_connection(self, "closed", lambda *__: self.disconnect_all())

  @staticmethod
  def _normalize_path(path: Union[str, Path]) -> str:
    return str(Path(path))

  @Gtk.Template.Callback()
  def _on_fetch_button_clicked(self, button: Gtk.Button) -> None:
    def on_all_done(*_args) -> None:
      self._fetch_going = False
      button.set_label(_("Fetch"))
      self.progress_revealer.set_reveal_child(False)

    def is_lrc_missing(track_uuid: str) -> bool:
      chronie = get_track_lyric(track_uuid)
      return not (chronie and "lrc" in chronie.exportable_formats())

    if not self._fetch_going:
      if self.log_items.get_n_items() != 0:
        self.log_items.remove_all()
        self.disconnect_all()
      if getattr(self, "_task_cancel_hdl", None) and getattr(self, "task", None):
        with contextlib.suppress(Exception):
          self.task.disconnect(unwrap(self._task_cancel_hdl))
      self._task_cancel_hdl = None
      if LibraryManager.current_library is None:
        return
      medias: list[BaseFile] = []
      self._path_to_uuid: dict[str, str] = {}
      for track in LibraryManager.list_tracks():
        media_path = LibraryManager.track_path(
          cast("str", track.track_uuid), cast("str", track.format)
        )
        media = parse_file(media_path)
        if media is None:
          continue
        if not self.rewrite_already_existing_switch.get_active() and not is_lrc_missing(
          cast("str", track.track_uuid)
        ):
          continue
        medias.append(media)
        self._path_to_uuid[self._normalize_path(media.path)] = cast(
          "str", track.track_uuid
        )
      if len(medias) == 0:
        self.fetch_log_list_box.set_placeholder(self.already_fetched)
        return
      self.task = AsyncTask(
        LRClibService().fetch_lyrics_many,  # ty:ignore[invalid-argument-type]
        medias,
        do_use_progress=True,
        do_use_cancellable=True,
      )
      self._task_cancel_hdl = self.task.connect("cancelled", self._on_task_cancelled)
      self.task.connect("notify::progress", self._on_progress_change)
      self.task.start()
      self._fetch_going = True
      self.progress_revealer.set_reveal_child(True)
      self.progress_bar.set_fraction(0.0)
      self.new_connection(
        LRClibService(),
        "fetch-started",
        lambda _lrclib, path: self.log_items.insert(
          0, LogEntry(self._normalize_path(path))
        ),
      )
      self.new_connection(
        LRClibService(),
        "fetch-message",
        self._on_fetch_message,
      )
      self.new_connection(
        LRClibService(),
        "fetch-state",
        self._on_fetch_state,
      )
      self.new_connection(
        LRClibService(),
        "fetch-all-done",
        on_all_done,
      )
      button.set_label(_("Cancel"))
    else:
      self.task.cancel()
      self._fetch_going = False
      button.set_label(_("Fetch"))

  def _on_progress_change(self, task: AsyncTask, _pspec) -> None:
    self.progress_bar.set_fraction(task.progress)

  def _on_fetch_state(
    self,
    _lrclib,
    path: str,
    state: FetchStates,
    entry: Optional[Union[LRClibEntry, Exception]],
  ) -> None:
    path = self._normalize_path(path)
    if entry is None:
      state = FetchStates.FAILED
    for item in self.log_items:
      item = cast("LogEntry", item)
      if item.path == path:
        if isinstance(entry, Exception):
          state = FetchStates.FAILED
          match entry:
            case httpx.ConnectTimeout:
              item.props.message = _("Connection timed out")  # ty:ignore[unresolved-attribute]
            case httpx.ConnectError:
              item.props.message = _("Connection error occurred")  # ty:ignore[unresolved-attribute]
            case __:
              item.props.message = _("An error occurred: ") + str(entry)  # ty:ignore[unresolved-attribute]
        # fmt: off
        match state:
          case FetchStates.DONE:
            entry = cast("LRClibEntry", entry)
            if entry.instrumental:
              item.props.instrumental = True  # ty:ignore[unresolved-attribute]
              item.props.message = _("Instrumental track. No lyrics available")  # ty:ignore[unresolved-attribute]
              return
            dl_profile = Schema.get(
              "root.settings.general.mass-downloading.preferred-format"
            )
            track_uuid = self._path_to_uuid.get(path)
            if not track_uuid:
              item.props.failed = True  # ty:ignore[unresolved-attribute]
              item.props.message = _("Track is missing from library")  # ty:ignore[unresolved-attribute]
              return
            match dl_profile:
              case "s":
                if entry.synced_lyrics and entry.synced_lyrics.strip() != "":
                  save_track_lyric(track_uuid, chronie_from_text(entry.synced_lyrics))
                  self._refresh_card(track_uuid)
                  item.props.done = True  # ty:ignore[unresolved-attribute]
                  return
                item.props.failed = True  # ty:ignore[unresolved-attribute]
                item.props.message = _("No synced lyrics found")  # ty:ignore[unresolved-attribute]
              case "s~p":
                if entry.synced_lyrics and entry.synced_lyrics.strip() != "":
                  save_track_lyric(track_uuid, chronie_from_text(entry.synced_lyrics))
                  self._refresh_card(track_uuid)
                  item.props.done = True  # ty:ignore[unresolved-attribute]
                elif entry.plain_lyrics.strip() != "":
                  save_track_lyric(track_uuid, chronie_from_text(entry.plain_lyrics))
                  self._refresh_card(track_uuid)
                  item.props.done = True  # ty:ignore[unresolved-attribute]
                else:
                  item.props.failed = True  # ty:ignore[unresolved-attribute]
                  item.props.message = _("No lyrics found")  # ty:ignore[unresolved-attribute]
              case "p":
                if entry.plain_lyrics.strip() != "":
                  save_track_lyric(track_uuid, chronie_from_text(entry.plain_lyrics))
                  self._refresh_card(track_uuid)
                  item.props.done = True  # ty:ignore[unresolved-attribute]
                  return
                item.props.failed = True  # ty:ignore[unresolved-attribute]
                item.props.message = _("No plain lyrics found")  # ty:ignore[unresolved-attribute]
          case FetchStates.FAILED: item.props.failed = True  # ty:ignore[unresolved-attribute]
          case FetchStates.CANCELLED: item.props.cancelled = True  # ty:ignore[unresolved-attribute]
        # fmt: on
        break

  def _on_fetch_message(self, _lrclib, path: str, message: str) -> None:
    path = self._normalize_path(path)
    for item in self.log_items:
      item = cast("LogEntry", item)
      if item.path == path:
        item.set_property("message", message)
        break

  def _on_task_cancelled(self, *_args) -> None:
    for item in self.log_items:
      if not (
        item.props.done  # ty:ignore[unresolved-attribute]
        or item.props.failed  # ty:ignore[unresolved-attribute]
        or item.props.cancelled  # ty:ignore[unresolved-attribute]
        or item.props.instrumental,  # ty:ignore[unresolved-attribute]
      ):
        item.set_property("cancelled", True)
        item.set_property("message", _("Cancelled"))

  def _refresh_card(self, track_uuid: str) -> None:
    try:
      cards = Constants.WIN.library.cards_model
    except AttributeError:
      return
    for index in range(cards.get_n_items()):
      model = cast("SongCardModel", cards.get_item(index))
      if model and model.uuid == track_uuid:
        model.refresh_available_lyrics()
        break

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
  message: str = cast("str", GObject.Property(type=str, default=""))
  failed: bool = cast("bool", GObject.Property(type=bool, default=False))
  done: bool = cast("bool", GObject.Property(type=bool, default=False))
  cancelled: bool = cast("bool", GObject.Property(type=bool, default=False))
  instrumental: bool = cast("bool", GObject.Property(type=bool, default=False))

  def __init__(self, path: str, message: str = _("Fetching")) -> None:
    super().__init__(message=message)
    self.path = path
