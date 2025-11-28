"""Word-by-Word syncing page"""

import traceback
from pathlib import Path
from typing import Literal, Optional, Union

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from chronograph.backend.converter import ns_to_timestamp, timestamp_to_ns
from chronograph.backend.file import SongCardModel
from chronograph.backend.lyrics import (
  Lyrics,
  LyricsFile,
  LyricsFormat,
  LyricsHierarchyConversion,
)
from chronograph.backend.media import FileID3, FileMP4, FileUntaggable, FileVorbis
from chronograph.backend.player import Player
from chronograph.backend.wbw.models.lyrics_model import LyricsModel
from chronograph.internal import Constants, Schema
from chronograph.ui.dialogs.resync_all_alert_dialog import ResyncAllAlertDialog
from chronograph.ui.widgets.ui_player import UIPlayer
from dgutils import Actions

gtc = Gtk.Template.Child
logger = Constants.LOGGER


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/sync_pages/WBWSyncPage.ui")
@Actions.from_schema(Constants.PREFIX + "/resources/actions/wbw_sync_page_actions.yaml")
class WBWSyncPage(Adw.NavigationPage):
  __gtype_name__ = "WBWSyncPage"

  player_container: Gtk.Box = gtc()
  rew_button: Gtk.Button = gtc()
  forw_button: Gtk.Button = gtc()
  modes: Adw.ViewStack = gtc()
  edit_view_stack_page: Adw.ViewStackPage = gtc()
  edit_view_text_view: Gtk.TextView = gtc()
  sync_view_stack_page: Adw.ViewStackPage = gtc()
  lyrics_layout_container: Adw.Bin = gtc()

  _lyrics_model: LyricsModel
  _autosave_timeout_id: Optional[int] = None
  _lyrics_model: Optional[LyricsModel] = None

  def __init__(self, card_model: SongCardModel) -> None:
    def on_shown(*_args) -> None:
      if isinstance(self._card.mfile, FileUntaggable):
        self.action_set_enabled("controls.edit_metadata", enabled=False)

    super().__init__()

    # Workaround, since Adw.InlineViewSwitcher doen't have singnal for describing
    # previous and newly selected page
    self._current_page: Adw.ViewStackPage = self.edit_view_stack_page
    self._previous_page: Optional[Adw.ViewStackPage] = None

    # Player setup
    self._card: SongCardModel = card_model
    self._file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable] = card_model.mfile
    self._lyrics_file = self._card.lyrics_file
    self._card.bind_property(
      "title_display", self, "title", GObject.BindingFlags.SYNC_CREATE
    )
    if isinstance(self._card.mfile, FileUntaggable):
      self.action_set_enabled("controls.edit_metadata", enabled=False)
    self._player_widget = UIPlayer(card_model)
    self.player_container.append(self._player_widget)

    self._close_rq_handler_id = Constants.WIN.connect(
      "close-request", self._on_app_close
    )

    self.connect("showing", on_shown)

    self.modes.connect("notify::visible-child", self._page_visibility)
    self.connect("hidden", self._on_page_closed)

    # Automatically load the lyrics file if it exists
    if Schema.get("root.settings.file-manipulation.enabled"):
      lines = None
      if self._lyrics_file.elrc_lyrics.text != "":
        lines = self._lyrics_file.elrc_lyrics.get_normalized_lines()
      elif self._lyrics_file.lrc_lyrics.text != "":
        lines = self._lyrics_file.lrc_lyrics.get_normalized_lines()

      if lines is not None:
        buffer = Gtk.TextBuffer()
        buffer.set_text("\n".join(lines).strip())
        self.edit_view_text_view.set_buffer(buffer)

  def _page_visibility(self, stack: Adw.ViewStack, _pspec) -> None:
    page: Adw.ViewStackPage = stack.get_page(stack.get_visible_child())
    self._previous_page = self._current_page
    self._current_page = page
    self._on_page_switched(self._previous_page, self._current_page)

  def _on_page_switched(
    self, prev_page: Adw.ViewStackPage, new_page: Adw.ViewStackPage
  ) -> None:
    self._autosave()
    if prev_page == self.edit_view_stack_page and new_page == self.sync_view_stack_page:
      lyrics = self.edit_view_text_view.get_buffer().get_text(
        self.edit_view_text_view.get_buffer().get_start_iter(),
        self.edit_view_text_view.get_buffer().get_end_iter(),
        include_hidden_chars=False,
      )
      if lyrics != "":
        self.lyrics_layout_container.set_child((model := LyricsModel(lyrics)).widget)
        self._lyrics_model = model
        latest_unsynced_line = model.get_latest_unsynced()
        if latest_unsynced_line is not None:
          latest_unsynced_word = latest_unsynced_line[0].get_latest_unsynced()
          model.set_current(latest_unsynced_line[1])
          if latest_unsynced_word is not None:
            latest_unsynced_line[0].set_current(latest_unsynced_word[1])
        else:
          self._lyrics_model.set_current(0)
      else:
        self.lyrics_layout_container.set_child(
          Adw.StatusPage(
            title=_("No lyrics available"),
            description=_("You've not provided any lyrics for synchronization"),
            icon_name="nothing-found-symbolic",
          )
        )

    elif (
      prev_page == self.sync_view_stack_page and new_page == self.edit_view_stack_page
    ):
      try:
        lyrics = Lyrics.from_tokens(self._lyrics_model.get_tokens()).text
        buffer = Gtk.TextBuffer()
        buffer.set_text(lyrics)
        self.edit_view_text_view.set_buffer(buffer)
      except AttributeError:
        pass

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

  ############### Import Actions ###############
  def _import_lrclib(self, *_args) -> None:
    from chronograph.ui.dialogs.lrclib import LRClib

    lrclib_dialog = LRClib(self._card.title, self._card.artist, self._card.album)
    lrclib_dialog.present(Constants.WIN)
    logger.debug("LRClib import dialog shown")

  def _import_file(self, *_args) -> None:
    def on_selected_lyrics_file(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      path = file_dialog.open_finish(result).get_path()

      buffer = Gtk.TextBuffer()
      buffer.set_text(Lyrics(Path(path).read_text()).text.strip())
      self.edit_view_text_view.set_buffer(buffer)
      logger.info("Imported lyrics from file")

    dialog = Gtk.FileDialog(default_filter=Gtk.FileFilter(mime_types=["text/plain"]))
    dialog.open(Constants.WIN, None, on_selected_lyrics_file)

  def _import_clipboard(self, *_args) -> None:
    def on_clipboard_parsed(
      _clipboard, result: Gio.Task, clipboard: Gdk.Clipboard
    ) -> None:
      data = clipboard.read_text_finish(result)
      buffer = Gtk.TextBuffer()
      buffer.set_text(data)
      self.edit_view_text_view.set_buffer(buffer)
      logger.info("Imported lyrics from clipboard")

    clipboard = Gdk.Display().get_default().get_clipboard()
    clipboard.read_text_async(None, on_clipboard_parsed, user_data=clipboard)

  ###############

  ############### Export Actions ###############
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

    if self._current_page == self.edit_view_stack_page:
      lyrics = self.edit_view_text_view.get_buffer().get_text(
        self.edit_view_text_view.get_buffer().get_start_iter(),
        self.edit_view_text_view.get_buffer().get_end_iter(),
        include_hidden_chars=False,
      )
    elif not isinstance(self.lyrics_layout_container.get_child(), Adw.StatusPage):
      lyrics = Lyrics.from_tokens(self._lyrics_model.get_tokens()).text
    else:
      lyrics = ""

    dialog = Gtk.FileDialog(
      initial_name=Path(self._file.path).stem
      + Schema.get("root.settings.file-manipulation.format")
    )
    dialog.save(Constants.WIN, None, on_export_file_selected, lyrics)

  def _export_clipboard(self, *_args) -> None:
    if self._current_page == self.edit_view_stack_page:
      lyrics = self.edit_view_text_view.get_buffer().get_text(
        self.edit_view_text_view.get_buffer().get_start_iter(),
        self.edit_view_text_view.get_buffer().get_end_iter(),
        include_hidden_chars=False,
      )
    elif not isinstance(self.lyrics_layout_container.get_child(), Adw.StatusPage):
      lyrics = Lyrics.from_tokens(self._lyrics_model.get_tokens()).text
    else:
      lyrics = ""
    clipboard = Gdk.Display().get_default().get_clipboard()
    clipboard.set(lyrics)
    logger.info("Lyrics exported to clipboard")
    Constants.WIN.show_toast(_("Lyrics exported to clipboard"), timeout=3)

  ###############

  ############### Sync Actions ###############
  def _sync(self, *_args) -> None:
    current_line = self._lyrics_model.get_current_line()
    current_word = current_line.get_current_word()
    ns = Player()._gst_player.props.position  # noqa: SLF001
    ms = ns // 1_000_000
    current_word.set_property("time", ms)
    logger.debug(
      "Word “%s” was synced with timestamp %s",
      current_word.word,
      ns_to_timestamp(ns),
    )
    current_line.next()
    self.reset_timer()

  def _replay(self, *_args) -> None:
    current_line = self._lyrics_model.get_current_line()
    current_word = current_line.get_current_word()
    ns = timestamp_to_ns(
      f"[{current_word.timestamp}]"
    )  # I'm lazy to refactor this method, so `[]` were added :)
    Player().seek(ns // 1_000_000)
    logger.debug("Replayed word at timing: %s", ns_to_timestamp(ns))

  def _seek(self, _action, _param, direction: bool, large: bool = False) -> None:
    if direction:
      if not large:
        mcs_seek = Schema.get("root.settings.syncing.seek.wbw.def") * 1_000
      else:
        mcs_seek = Schema.get("root.settings.syncing.seek.wbw.large") * 1_000
    elif not large:
      mcs_seek = Schema.get("root.settings.syncing.seek.wbw.def") * 1_000 * -1
    else:
      mcs_seek = Schema.get("root.settings.syncing.seek.wbw.large") * 1_000 * -1
    current_line = self._lyrics_model.get_current_line()
    current_word = current_line.get_current_word()
    ms = current_word.time
    ns = ms * 1_000_000
    ns_new = ns + mcs_seek * 1_000
    ns_new = max(ns_new, 0)
    current_word.set_property("time", ns_new // 1_000_000)
    Player().seek(ns_new // 1_000_000)
    logger.debug(
      "Word(%s) was seeked %sms to %s",
      current_word,
      mcs_seek // 1000,
      ns_to_timestamp(ns_new),
    )
    self.reset_timer()

  def resync_all(self, ms: int, backwards: bool = False) -> None:
    """Re-syncs all words to a provided amount of milliseconds

    Parameters
    ----------
    ms : int
        Milliseconds
    backwards : bool, optional
        Is re-sync back, by default False
    """
    for line in self._lyrics_model:
      for word in line:
        prev_time = word.time
        time = (prev_time - ms) if backwards else (prev_time + ms)
        word.time = max(time, 0)
    logger.info(
      "All word were resynced %sms %s",
      ms,
      "backwards" if backwards else "forward",
    )

  ###############

  ############### Utilities Actions ###############

  def _resync_all_lines(self, *_args) -> None:
    if (
      self._current_page == self.sync_view_stack_page and self._lyrics_model is not None
    ):
      dialog = ResyncAllAlertDialog(self)
      dialog.present(Constants.WIN)
      dialog.get_extra_child().grab_focus()
    elif self._current_page == self.sync_view_stack_page and self._lyrics_model is None:
      Constants.WIN.show_toast(_("No lyrics to be re-synced"), 2)
    else:
      Constants.WIN.show_toast(_("Open Sync mode to re-sync all words"), 2)

  ###############

  ############### Navigation Actions ###############
  def _nav_prev(self, *_args) -> None:
    self._lyrics_model.get_current_line().previous()

  def _nav_next(self, *_args) -> None:
    self._lyrics_model.get_current_line().next()

  def _nav_up(self, *_args) -> None:
    self._lyrics_model.previous()

  def _nav_down(self, *_args) -> None:
    self._lyrics_model.next()

  ###############

  ############### Autosave Actions ###############

  def reset_timer(self) -> None:
    """Resets throttling timer of `_autosave` call"""
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
        if (
          self.modes.get_page(self.modes.get_visible_child())
          == self.edit_view_stack_page
        ):
          lyrics = Lyrics(
            self.edit_view_text_view.get_buffer().get_text(
              self.edit_view_text_view.get_buffer().get_start_iter(),
              self.edit_view_text_view.get_buffer().get_end_iter(),
              include_hidden_chars=False,
            )
          )
        else:
          lyrics = Lyrics.from_tokens(self._lyrics_model.get_tokens())
        if Schema.get("root.settings.file-manipulation.lrc-along-elrc") and (
          Schema.get("root.settings.file-manipulation.elrc-prefix") != ""
        ):
          try:
            self._lyrics_file.lrc_lyrics.text = lyrics.of_format(LyricsFormat.LRC)
            self._lyrics_file.lrc_lyrics.save()
            logger.debug("LRC lyrics autosaved successfully")
          except LyricsHierarchyConversion:
            logger.debug("Prevented overwriting LRC lyrics with Plain in LRC file")
        try:
          self._lyrics_file.elrc_lyrics.text = lyrics.of_format(LyricsFormat.ELRC)
          if Schema.get("root.settings.file-manipulation.embed-lyrics.enabled"):
            self._file.embed_lyrics(
              self._lyrics_file.elrc_lyrics.text
              if self._lyrics_file.elrc_lyrics.text
              else None
            )
          self._lyrics_file.elrc_lyrics.save()
          logger.debug("eLRC lyrics autosaved successfully")
        except LyricsHierarchyConversion:
          logger.debug(
            "Prevented overwriting eLRC lyrics with LRC or Plain in eLRC file"
          )
      except AttributeError:
        pass
      except Exception:
        logger.warning("Autosave failed: %s", traceback.format_exc())
      self._autosave_timeout_id = None
    return False

  def _on_page_closed(self, *_args) -> None:
    Constants.WIN.disconnect(self._close_rq_handler_id)
    if self._autosave_timeout_id:
      GLib.source_remove(self._autosave_timeout_id)
    if Schema.get("root.settings.file-manipulation.enabled"):
      logger.debug("Page closed, saving lyrics")
      self._autosave()
    Player().stop()
    self._player_widget.link_teardown()

  def _on_app_close(self, *_) -> None:
    if self._autosave_timeout_id:
      GLib.source_remove(self._autosave_timeout_id)
    if Schema.get("root.settings.file-manipulation.enabled"):
      logger.debug("App closed, saving lyrics")
      self._autosave()
    return False

  ###############
