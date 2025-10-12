"""Sync page for LRC format syncing"""

import hashlib
import re
import threading
import traceback
from binascii import unhexlify
from pathlib import Path
from typing import Literal, Optional, Union

import requests
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from chronograph.internal import Constants, Schema
from chronograph.ui.dialogs.resync_all_alert_dialog import ResyncAllAlertDialog
from chronograph.ui.widgets.song_card import SongCard
from chronograph.ui.widgets.ui_player import UIPlayer
from chronograph.utils.converter import ns_to_timestamp, timestamp_to_ns
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable
from chronograph.utils.lyrics import Lyrics, LyricsFile, LyricsFormat
from chronograph.utils.player import Player
from dgutils import Actions

gtc = Gtk.Template.Child  # pylint: disable=invalid-name
logger = Constants.LOGGER
lrclib_logger = Constants.LRCLIB_LOGGER

PANGO_HIGHLIGHTER = Pango.AttrList().from_string("0 -1 weight ultrabold")


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/sync_pages/LRCSyncPage.ui")
@Actions.from_schema(Constants.PREFIX + "/resources/actions/lrc_sync_page_actions.yaml")
class LRCSyncPage(Adw.NavigationPage):
  __gtype_name__ = "LRCSyncPage"

  header_bar: Adw.HeaderBar = gtc()
  player_container: Gtk.Box = gtc()
  rew_button: Gtk.Button = gtc()
  forw_button: Gtk.Button = gtc()
  export_lyrics_button: Gtk.MenuButton = gtc()
  sync_lines_scrolled_window: Gtk.ScrolledWindow = gtc()
  sync_lines: Gtk.ListBox = gtc()
  selected_line: Optional["LRCSyncLine"] = None

  _autosave_timeout_id: Optional[int] = None

  def __init__(
    self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
  ) -> None:
    def on_shown(*_args) -> None:
      if isinstance(self._card._file, FileUntaggable):  # noqa: SLF001
        self.action_set_enabled("controls.edit_metadata", enabled=False)

    super().__init__()
    self._card: SongCard = card
    self._lyrics_file = card._lyrics_file  # noqa: SLF001
    self._file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable] = file
    self._card.bind_property("title", self, "title", GObject.BindingFlags.SYNC_CREATE)
    if isinstance(self._card._file, FileUntaggable):  # noqa: SLF001
      self.action_set_enabled("controls.edit_metadata", enabled=False)
    self._player_widget = UIPlayer(file, card)
    self.player_container.append(self._player_widget)
    Player()._gst_player.connect("pos-upd", self._on_timestamp_changed)  # noqa: SLF001

    self.connect("showing", on_shown)
    self.connect("hidden", self._on_page_closed)
    self._close_rq_handler_id = Constants.WIN.connect(
      "close-request", self._on_app_close
    )

    # Automatically load the lyrics file if it exists
    if (
      Schema.get("root.settings.file-manipulation.enabled")
      and self._lyrics_file.lrc_lyrics.text != ""
    ):
      lines = self._lyrics_file.lrc_lyrics.get_normalized_lines()
      self.sync_lines.remove_all()
      for line in lines:
        self.sync_lines.append(LRCSyncLine(line))

  @Gtk.Template.Callback()
  def _on_seek_button_released(self, button: Gtk.Button) -> None:
    display = Constants.WIN.get_display()
    seat = display.get_default_seat()
    device = seat.get_keyboard()
    state = device.get_modifier_state()

    direction = button == self.forw_button
    large = False

    if state in (Gdk.ModifierType.CONTROL_MASK.value, 20):  # 20 is used on X11
      large = True
    self._seek(None, None, direction, large)

  def is_all_lines_synced(self) -> bool:
    """Determines if all lines have timestamp

    Returns
    -------
    bool
        If all lines have timestamp
    """
    # pylint: disable=not-an-iterable
    text = "\n".join([line.get_text() for line in self.sync_lines])
    timestamp_pattern = re.compile(r"\[\d{2}:\d{2}\.\d{2,3}]")
    return all(timestamp_pattern.search(line) for line in text.strip().splitlines())

  ############### Line Actions ###############
  def _append_end_line(self, *_args) -> None:
    self.sync_lines.append(LRCSyncLine())
    logger.debug("New line appended to the end of the sync lines")

  def append_line(self, *_args) -> None:
    if self.selected_line:
      for index, line in enumerate(self.sync_lines):
        if line == self.selected_line:
          self.sync_lines.insert(sync_line := LRCSyncLine(), index + 1)
          adj = self.sync_lines_scrolled_window.get_vadjustment()
          value = adj.get_value()
          sync_line.grab_focus()
          adj.set_value(value)
          logger.debug("New line appended to selected line(%s)", self.selected_line)
          return

  def _prepend_line(self, *_args) -> None:
    if self.selected_line:
      for index, line in enumerate(self.sync_lines):
        if line == self.selected_line:
          try:
            self.sync_lines.insert(LRCSyncLine(), index)
            logger.debug(
              "New line prepended to selected line(%s)",
              self.selected_line,
            )
            return
          except IndexError:
            self.sync_lines.prepend(LRCSyncLine())
            logger.debug("New line prepended to the list start")
            return

  def _remove_line(self, *_args) -> None:
    if self.selected_line:
      self.sync_lines.remove(self.selected_line)
      logger.debug("Selected line(%s) removed", self.selected_line)
      self.selected_line = None

  ###############

  ############### Sync Actions ###############
  def _sync(self, *_args) -> None:
    if self.selected_line:
      ns = Player()._gst_player.props.position  # noqa: SLF001
      timestamp = ns_to_timestamp(ns)
      pattern = re.compile(r"\[([^\[\]]+)\] ")
      if pattern.search(self.selected_line.get_text()) is None:
        self.selected_line.set_text(timestamp + self.selected_line.get_text())
      else:
        replacement = rf"{timestamp}"
        self.selected_line.set_text(
          re.sub(pattern, replacement, self.selected_line.get_text())
        )
      logger.debug("Line was synced with timestamp: %s", timestamp)

      for index, line in enumerate(self.sync_lines):
        if (
          line == self.selected_line
          and (row := self.sync_lines.get_row_at_index(index + 1)) is not None
        ):
          row.grab_focus()
          return

  def _replay(self, *_args) -> None:
    ns = timestamp_to_ns(self.selected_line.get_text())
    Player().seek(ns // 1_000_000)
    logger.debug("Replayed lines at timing: %s", ns_to_timestamp(ns))

  def _seek(self, _action, _param, direction: bool, large: bool = False) -> None:
    if direction:
      if not large:
        mcs_seek = Schema.get("root.settings.syncing.seek.lbl.def") * 1_000
      else:
        mcs_seek = Schema.get("root.settings.syncing.seek.lbl.large") * 1_000
    elif not large:
      mcs_seek = Schema.get("root.settings.syncing.seek.lbl.def") * 1_000 * -1
    else:
      mcs_seek = Schema.get("root.settings.syncing.seek.lbl.large") * 1_000 * -1
    pattern = re.compile(r"\[([^\[\]]+)\] ")
    match = pattern.search(self.selected_line.get_text())
    if match is None:
      return
    timestamp = match[0]
    ns = timestamp_to_ns(timestamp) + mcs_seek * 1_000
    ns = max(ns, 0)
    timestamp = ns_to_timestamp(ns)
    replacement = rf"{timestamp}"
    self.selected_line.set_text(
      re.sub(pattern, replacement, self.selected_line.get_text())
    )
    Player().seek(ns // 1_000_000)
    logger.debug(
      "Line(%s) was seeked %sms to %s",
      self.selected_line,
      mcs_seek // 1000,
      timestamp,
    )

  def resync_all(self, ms: int, backwards: bool = False) -> None:
    pattern = re.compile(r"\[([^\[\]]+)\] ")
    for line in self.sync_lines:  # pylint: disable=not-an-iterable
      line: LRCSyncLine
      match = pattern.search(line.get_text())
      if match is None:
        return
      timestamp = match[0]
      ns = timestamp_to_ns(timestamp)
      ns = (ns - ms * 1_000_000) if backwards else (ns + ms * 1_000_000)
      ns = max(ns, 0)
      timestamp = ns_to_timestamp(ns)
      replacement = rf"{timestamp}"
      line.set_text(re.sub(pattern, replacement, line.get_text()))
    logger.info(
      "All lines were resynced %sms %s",
      ms,
      "backwards" if backwards else "forward",
    )

  ###############

  ############### Import Actions ###############
  def _import_clipboard(self, *_args) -> None:
    def __on_clipboard_parsed(
      _clipboard, result: Gio.Task, clipboard: Gdk.Clipboard
    ) -> None:
      data = clipboard.read_text_finish(result)
      lines = data.splitlines()
      self.sync_lines.remove_all()
      for _, line in enumerate(lines):
        self.sync_lines.append(LRCSyncLine(line))
      logger.info("Imported lyrics from clipboard")

    clipboard = Gdk.Display().get_default().get_clipboard()
    clipboard.read_text_async(None, __on_clipboard_parsed, user_data=clipboard)

  def _import_file(self, *_args) -> None:
    def on_selected_lyrics_file(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      path = file_dialog.open_finish(result).get_path()

      self.sync_lines.remove_all()
      for _, line in enumerate(Lyrics(Path(path).read_text()).get_normalized_lines()):
        self.sync_lines.append(LRCSyncLine(line))
      logger.info("Imported lyrics from file")

    dialog = Gtk.FileDialog(default_filter=Gtk.FileFilter(mime_types=["text/plain"]))
    dialog.open(Constants.WIN, None, on_selected_lyrics_file)

  def _import_lrclib(self, *_args) -> None:
    from chronograph.ui.dialogs.lrclib import LRClib  # noqa: PLC0415

    lrclib_dialog = LRClib(self._card.title, self._card.artist, self._card.album)
    lrclib_dialog.present(Constants.WIN)
    logger.debug("LRClib import dialog shown")

  ###############

  ############### Export Actions ###############

  def _export_clipboard(self, *_args) -> None:
    string = ""
    for line in self.sync_lines:  # pylint: disable=not-an-iterable
      string += line.get_text() + "\n"
    string = string.strip()
    clipboard = Gdk.Display().get_default().get_clipboard()
    clipboard.set(string)
    logger.info("Lyrics exported to clipboard")
    Constants.WIN.show_toast(_("Lyrics exported to clipboard"), timeout=3)

  def _export_file(self, *_args) -> None:
    def on_export_file_selected(
      file_dialog: Gtk.FileDialog, result: Gio.Task, lyrics: str
    ) -> None:
      filepath = file_dialog.save_finish(result).get_path()
      LyricsFile(filepath).modify_lyrics(lyrics)
      logger.info("Lyrics exported to file: '%s'", filepath)

      Constants.WIN.show_toast(
        _("Lyrics exported to file"),
        button_label=_("Show"),
        button_callback=lambda *_: Gio.AppInfo.launch_default_for_uri(
          f"file://{Path(filepath).parent}"
        ),
      )

    lyrics = ""
    for line in self.sync_lines:  # pylint: disable=not-an-iterable
      lyrics += line.get_text() + "\n"
    dialog = Gtk.FileDialog(
      initial_name=Path(self._file.path).stem
      + Schema.get("root.settings.file-manipulation.format")
    )
    dialog.save(Constants.WIN, None, on_export_file_selected, lyrics)

  ###############

  def _on_timestamp_changed(self, _obj, pos: int) -> None:
    try:
      lines: list[LRCSyncLine] = []
      timestamps: list[int] = []
      for line in self.sync_lines:  # pylint: disable=not-an-iterable
        line.set_attributes(None)
        try:
          timing = timestamp_to_ns(line.get_text())
          lines.append(line)
          timestamps.append(timing)
        except ValueError:
          break

      if not timestamps:
        return

      timestamp = pos
      if timestamp < timestamps[0]:
        return
      for i in range(len(timestamps) - 1):
        if timestamps[i] <= timestamp < timestamps[i + 1]:
          lines[i].set_attributes(PANGO_HIGHLIGHTER)
          return
      if timestamp >= timestamps[-1]:
        lines[-1].set_attributes(PANGO_HIGHLIGHTER)
    except IndexError:
      pass

  ############### Utilities Actions ###############

  def _resync_all_lines(self, *_args) -> None:
    dialog = ResyncAllAlertDialog(self)
    dialog.present(Constants.WIN)
    dialog.get_extra_child().grab_focus()

  ###############

  ############### Autosave Actions ###############

  def reset_timer(self) -> None:
    if self._autosave_timeout_id:
      GLib.source_remove(self._autosave_timeout_id)
    if Schema.get("root.settings.file-manipulation.enabled"):
      self._autosave_timeout_id = GLib.timeout_add(
        Schema.get("root.settings.file-manipulation.throttling") * 1000,
        self._autosave,
      )

  def _autosave(self) -> Literal[False]:
    if Schema.get("root.settings.file-manipulation.enabled"):
      try:
        # pylint: disable=not-an-iterable
        lyrics = [line.get_text() for line in self.sync_lines]
        self._lyrics_file.lrc_lyrics.text = "\n".join(lyrics).strip()
        self._lyrics_file.lrc_lyrics.save()
        self._file.embed_lyrics(
          self._lyrics_file.lrc_lyrics if self._lyrics_file.lrc_lyrics.text else None
        )
        logger.debug("Lyrics autosaved successfully")
      except Exception:
        logger.warning("Autosave failed: %s", traceback.format_exc())
      self._autosave_timeout_id = None
    return False

  def _on_page_closed(self, *_args):
    Constants.WIN.disconnect(self._close_rq_handler_id)
    if self._autosave_timeout_id:
      GLib.source_remove(self._autosave_timeout_id)
    if Schema.get("root.settings.file-manipulation.enabled"):
      logger.debug("Page closed, saving lyrics")
      self._autosave()
    Player().stop()
    self._player_widget.disconnect_all()

  def _on_app_close(self, *_):
    if self._autosave_timeout_id:
      GLib.source_remove(self._autosave_timeout_id)
    if Schema.get("root.settings.file-manipulation.enabled"):
      logger.debug("App closed, saving lyrics")
      self._autosave()
    return False

  ###############

  ############### Publisher ###############

  def _publish(self, __, ___, card: SongCard) -> None:
    def verify_nonce(result: int, target: int) -> bool:
      if len(result) != len(target):
        return False

      for index, res in enumerate(result):
        if res > target[index]:
          return False
        if res < target[index]:
          break

      return True

    def solve_challenge(prefix: str, target_hex: str) -> str:
      target = unhexlify(target_hex.upper())
      nonce = 0

      while True:
        input_data = f"{prefix}{nonce}".encode()
        hashed = hashlib.sha256(input_data).digest()

        if verify_nonce(hashed, target):
          break
        nonce += 1

      return str(nonce)

    def do_publish(
      title: str, artist: str, album: str, duration: str, lyrics: Lyrics
    ) -> None:
      _err = None
      try:
        lrclib_logger.info("Connecting to lrclib.net/api/request-challenge")
        challenge_data = requests.post(
          url="https://lrclib.net/api/request-challenge", timeout=10
        )
        lrclib_logger.debug("LRClib cryptographic challenge was requested successfully")
      except requests.exceptions.ConnectionError as e:
        Constants.WIN.show_toast(_("Failed to connect to LRClib.net"))
        _err = e
      except requests.exceptions.Timeout as e:
        Constants.WIN.show_toast(_("Connection to LRClib.net timed out"))
        _err = e
      except Exception as e:
        Constants.WIN.show_toast(_("An error occurred while connecting to LRClib.net"))
        _err = e
      finally:
        if _err:
          lrclib_logger.warning("Publishing failed: %s", _err, stack_info=True)
          self.export_lyrics_button.set_sensitive(True)
          self.export_lyrics_button.set_icon_name("export-to-symbolic")
          return  # noqa: B012

      challenge_data = challenge_data.json()
      nonce = solve_challenge(
        prefix=challenge_data["prefix"], target_hex=challenge_data["target"]
      )
      lrclib_logger.info("X-Publish-Token: %s", f"{challenge_data['prefix']}:{nonce}")

      _err = None
      try:
        lrclib_logger.info("Connecting to lrclib.net/api/publish")
        response: requests.Response = requests.post(
          url="https://lrclib.net/api/publish",
          headers={
            "X-Publish-Token": f"{challenge_data['prefix']}:{nonce}",
            "Content-Type": "application/json",
          },
          params={"keep_headers": "true"},
          json={
            "trackName": title,
            "artistName": artist,
            "albumName": album,
            "duration": duration,
            "plainLyrics": lyrics.of_format(LyricsFormat.PLAIN),
            "syncedLyrics": lyrics.of_format(LyricsFormat.LRC),
          },
          timeout=10,
        )
        lrclib_logger.info("Established connection to lrclib.net")
      except requests.exceptions.ConnectionError as e:
        Constants.WIN.show_toast(_("Failed to connect to LRClib.net"))
        _err = e
      except requests.exceptions.Timeout as e:
        Constants.WIN.show_toast(_("Connection to LRClib.net timed out"))
        _err = e
      except Exception as e:
        Constants.WIN.show_toast(_("An error occurred while connecting to LRClib.net"))
        _err = e
      finally:
        self.export_lyrics_button.set_sensitive(True)
        self.export_lyrics_button.set_icon_name("export-to-symbolic")
        if _err:
          lrclib_logger.warning("Publishing failed: %s", _err, stack_info=True)
          return  # noqa: B012

      lrclib_logger.info("Publishing status code: %s", response.status_code)
      if response.status_code == 201:
        Constants.WIN.show_toast(
          _("Published successfully: {code}").format(code=str(response.status_code)),
        )
      elif response.status_code == 400:
        Constants.WIN.show_toast(
          _("Incorrect publish token: {code}").format(code=str(response.status_code)),
        )
      else:
        Constants.WIN.show_toast(
          _("Unknown error occured: {code}").format(code=str(response.status_code)),
        )

    title = card.title
    artist = card.artist
    album = card.album
    duration = card.duration
    # pylint: disable=not-an-iterable
    lyrics = Lyrics("\n".join(line.get_text() for line in self.sync_lines).rstrip("\n"))
    if not all((title, artist, album, duration, lyrics)):

      def reason(*_args) -> None:
        _alert = Adw.AlertDialog(
          heading=_("Unable to publish lyrics"),
          body=_(
            "To publish lyrics the track must have a title, artist, album and lyrics fields set"
          ),
          default_response="close",
          close_response="close",
        )
        _alert.add_response("close", _("Close"))
        _alert.present(Constants.WIN)

      Constants.WIN.show_toast(
        _("Cannot publish empty lyrics"),
        button_label=_("Why?"),
        button_callback=reason,
      )
      return
    if not self.is_all_lines_synced():
      Constants.WIN.show_toast(
        _("Seems like not every line is synced"),
      )
      return
    self.export_lyrics_button.set_sensitive(False)
    self.export_lyrics_button.set_child(Adw.Spinner())
    threading.Thread(
      target=do_publish,
      args=(title, artist, album, duration, lyrics),
      daemon=True,
    ).start()

  ###############


class LRCSyncLine(Adw.EntryRow):
  __gtype_name__ = "LRCSyncLine"

  def __init__(self, text: str = "") -> None:
    super().__init__(editable=True, text=text)
    self.add_css_class("property")
    self.focus_controller = Gtk.EventControllerFocus()
    self.focus_controller.connect("enter", self._on_selected)
    self.add_controller(self.focus_controller)
    self.connect("entry-activated", self.add_line_on_enter)
    self.connect("changed", self._reset_timer)

    for item in self.get_child():
      for _item in item:
        if isinstance(_item, Gtk.Text):
          self.text_field = _item
          break
    self.text_field.connect("backspace", self._remove_line_on_backspace)

  def add_line_on_enter(self, *_args) -> None:
    """Add a new line when Enter is pressed"""
    self.get_ancestor(LRCSyncPage).append_line()
    logger.debug("A new line added underneath of %s", self)

  def _on_selected(self, *_args) -> None:
    self.get_ancestor(LRCSyncPage).selected_line = self

  def _reset_timer(self, *_args) -> None:
    self.get_ancestor(LRCSyncPage).reset_timer()

  def _remove_line_on_backspace(self, text: Gtk.Text) -> None:
    if text.get_text_length() == 0:
      page: LRCSyncPage = self.get_ancestor(LRCSyncPage)
      lines = []
      for line in page.sync_lines:
        lines.append(line)  # noqa: PERF402
      index = lines.index(self)
      page.sync_lines.remove(self)
      if (row := page.sync_lines.get_row_at_index(index - 1)) is not None:
        row.grab_focus()
      logger.debug("Line(%s) was removed from sync_lines", self)
