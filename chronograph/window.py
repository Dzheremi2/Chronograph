# TODO: Implement TTML (Timed Text Markup Language) support
# TODO: Implement LRC metatags support

import json
from enum import Enum
from gettext import ngettext
from pathlib import Path
from typing import Callable, Optional, Union

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from chronograph.backend.asynchronous.async_task import AsyncTask
from chronograph.backend.db.models import SchemaInfo
from chronograph.backend.file.library_manager import LibraryManager
from chronograph.backend.file.song_card_model import SongCardModel
from chronograph.backend.file_parsers import parse_file
from chronograph.backend.lyrics import save_track_lyric
from chronograph.backend.miscellaneous import (
  decode_filter_schema,
  encode_filter_schema,
)
from chronograph.internal import Constants, Schema
from chronograph.ui.dialogs.import_dialog import ImportDialog
from chronograph.ui.dialogs.importing_dialog import ImportingDialog
from chronograph.ui.dialogs.mass_downloading_dialog import MassDownloadingDialog
from chronograph.ui.dialogs.preferences import ChronographPreferences
from chronograph.ui.dialogs.tag_registration_dialog import TagRegistrationDialog
from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
from chronograph.ui.sync_pages.wbw_sync_page import WBWSyncPage
from chronograph.ui.widgets.library import Library
from chronograph.ui.widgets.tag_row import TagRow

gtc = Gtk.Template.Child
logger = Constants.LOGGER

MIME_TYPES = (
  "audio/mpeg",
  "audio/aac",
  "audio/ogg",
  "audio/x-vorbis+ogg",
  "audio/flac",
  "audio/vnd.wave",
  "audio/mp4",
)

MIME_TYPE_FILTERS = Gio.ListStore.new(Gtk.FileFilter)
MIME_TYPE_FILTERS.append(
  Gtk.FileFilter(mime_types=MIME_TYPES, name=_("All Supported Media"))
)
for mime in MIME_TYPES:
  filter_ = Gtk.FileFilter(mime_types=[mime])
  MIME_TYPE_FILTERS.append(filter_)


class WindowState(Enum):
  """Enum for window states"""

  NO_LIBRARY = 0
  EMPTY_LIBRARY = 1
  LIBRARY = 2


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/window.ui")
class ChronographWindow(Adw.ApplicationWindow):
  """App window class"""

  __gtype_name__ = "ChronographWindow"

  # Status pages
  no_saves_found_status: Adw.StatusPage = gtc()
  empty_library: Adw.StatusPage = gtc()
  empty_filter_results: Adw.StatusPage = gtc()

  # Library view widgets
  dnd_area_revealer: Gtk.Revealer = gtc()
  toast_overlay: Adw.ToastOverlay = gtc()
  window_state_stack: Gtk.Stack = gtc()
  no_library_view: Gtk.Box = gtc()
  navigation_view: Adw.NavigationView = gtc()
  library_nav_page: Adw.NavigationPage = gtc()
  overlay_split_view: Adw.OverlaySplitView = gtc()
  sidebar_window: Gtk.ScrolledWindow = gtc()
  sidebar: Gtk.ListBox = gtc()
  open_source_button: Gtk.MenuButton = gtc()
  left_buttons_revealer: Gtk.Revealer = gtc()
  search_bar: Gtk.SearchBar = gtc()
  search_entry: Gtk.SearchEntry = gtc()
  right_buttons_revealer: Gtk.Revealer = gtc()
  proceed_bulk_delete_button_revealer: Gtk.Revealer = gtc()
  enable_bulk_delete_button: Gtk.ToggleButton = gtc()
  library_overlay: Gtk.Overlay = gtc()
  library_scrolled_window: Gtk.ScrolledWindow = gtc()
  library_stack: Gtk.Stack = gtc()
  library: Library = gtc()

  # Quick Editor
  quick_edit_dialog: Adw.Dialog = gtc()
  quck_editor_toast_overlay: Adw.ToastOverlay = gtc()
  quick_edit_text_view: Gtk.TextView = gtc()
  quick_edit_copy_button: Gtk.Button = gtc()

  filter_none: bool = GObject.Property(type=bool, default=True)
  filter_plain: bool = GObject.Property(type=bool, default=True)
  filter_lrc: bool = GObject.Property(type=bool, default=True)
  filter_elrc: bool = GObject.Property(type=bool, default=True)
  reparse_action_done: bool = GObject.Property(type=bool, default=True)

  sort_state: str = Schema.get("root.state.library.sorting")

  def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)

    logger.debug("Creating window")
    self._import_task: Optional[AsyncTask] = None
    self._import_dialog: Optional[ImportingDialog] = None

    # Apply devel window decorations
    if Constants.APP_ID.endswith(".Devel"):
      logger.debug("Devel detected, enabling devel window decorations")
      self.add_css_class("devel")

    # Create a WindowState property for automatic window UI state updates
    self._state: WindowState = WindowState.NO_LIBRARY
    self.connect("notify::state", self._state_changed)

    # Connect the search entry to the search bar
    self.search_bar.connect_entry(self.search_entry)

    # Drag'N'Drop setup
    self.drop_target = Gtk.DropTarget(
      actions=Gdk.DragAction.COPY,
      formats=Gdk.ContentFormats.new_for_gtype(Gdk.FileList),
    )
    self.drop_target.connect("accept", self._on_drag_accept)
    self.drop_target.connect("enter", self._on_drag_enter)
    self.drop_target.connect("leave", self._on_drag_leave)
    self.drop_target.connect("drop", self._on_drag_drop)
    self.add_controller(self.drop_target)

    # Building up the sidebar with tag bookmarks
    self.active_tag_filter: Optional[str] = None
    self.sidebar.set_placeholder(self.no_saves_found_status)

    # Setup filter by lyrics format
    (
      self.props.filter_none,
      self.props.filter_plain,
      self.props.filter_lrc,
      self.props.filter_elrc,
    ) = (
      decode_filter_schema(0),
      decode_filter_schema(1),
      decode_filter_schema(2),
      decode_filter_schema(3),
    )
    filter_none_action = Gio.PropertyAction.new("filter_none", self, "filter_none")
    self.add_action(filter_none_action)
    filter_plain_action = Gio.PropertyAction.new("filter_plain", self, "filter_plain")
    self.add_action(filter_plain_action)
    filter_lrc_action = Gio.PropertyAction.new("filter_lrc", self, "filter_lrc")
    self.add_action(filter_lrc_action)
    filter_elrc_action = Gio.PropertyAction.new("filter_elrc", self, "filter_elrc")
    self.add_action(filter_elrc_action)
    self.connect("notify::filter-none", self._on_filter_state)
    self.connect("notify::filter-plain", self._on_filter_state)
    self.connect("notify::filter-lrc", self._on_filter_state)
    self.connect("notify::filter-elrc", self._on_filter_state)

    Schema.bind("root.state.window.sidebar", self.overlay_split_view, "show-sidebar")

  def build_sidebar(self) -> None:
    """Builds the sidebar with tag bookmarks"""
    logger.debug("Building the sidebar")
    self.sidebar.remove_all()
    if LibraryManager.current_library is None:
      self.active_tag_filter = None
      return
    tags = self._get_registered_tags()
    for tag in tags:
      self.sidebar.append(TagRow(tag))
    self.sidebar.set_placeholder(self.no_saves_found_status)
    if self.active_tag_filter and self.active_tag_filter not in tags:
      self.active_tag_filter = None
      self.library.filter.changed(Gtk.FilterChange.DIFFERENT)

  def _get_registered_tags(self) -> list[str]:
    try:
      raw = SchemaInfo.get_by_id("tags").value
    except (SchemaInfo.DoesNotExist, AttributeError):
      return []
    try:
      tags = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
      return []
    return tags if isinstance(tags, list) else []

  def on_toggle_sidebar_action(self, *_args) -> None:
    """Toggle sidebar visibility"""
    logger.debug("Toggling sidebar")
    if self.navigation_view.get_visible_page() is self.library_nav_page:
      self.overlay_split_view.set_show_sidebar(
        not self.overlay_split_view.get_show_sidebar()
      )

  def on_open_mass_downloading_action(self, *_args) -> None:
    """Shows mass downloading dialog"""
    MassDownloadingDialog().present(self)

  def on_toggle_search_action(self, *_args) -> None:
    """Toggles search field of `self`"""
    if self.state in (WindowState.NO_LIBRARY, WindowState.EMPTY_LIBRARY):
      return

    if self.navigation_view.get_visible_page() == self.library_nav_page:
      search_bar = self.search_bar
      search_entry = self.search_entry
    else:
      return

    search_bar.set_search_mode(not (search_mode := search_bar.get_search_mode()))

    if not search_mode:
      self.set_focus(search_entry)

    search_entry.set_text("")
    logger.debug("Search toggled")

  def on_show_preferences_action(self, *_args) -> None:
    """Shows the preferences dialog"""
    preferences = ChronographPreferences()
    preferences.present(self)
    logger.debug("Showing preferences")

  ############### Actions for opening files and directories ###############
  def on_open_library_action(self, *_args) -> None:
    """Selects a directory to open in the library"""

    def select_dir() -> None:
      logger.debug("Showing directory selection dialog")
      dialog = Gtk.FileDialog(
        default_filter=Gtk.FileFilter(mime_types=["inode/directory"])
      )
      dialog.select_folder(self, None, on_selected_dir)

    def on_selected_dir(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      try:
        _dir = file_dialog.select_folder_finish(result)
        if _dir is not None:
          dir_path = _dir.get_path()
          if dir_path and (Path(dir_path) / "is_chr_library").exists():
            self.open_library(dir_path)
          elif dir_path:
            self.show_toast(_("Only Chronograph libraries are supported"), 3)
      except GLib.GError:
        pass

    select_dir()

  def on_import_files_action(self, *_args) -> None:
    """Selects files to import into the library"""

    def select_files(*_args) -> None:
      logger.debug("Showing files selection dialog")
      dialog = Gtk.FileDialog(
        default_filter=MIME_TYPE_FILTERS[0], filters=MIME_TYPE_FILTERS
      )
      dialog.open_multiple(self, None, on_select_files)

    def on_select_files(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      try:
        files = [
          file.get_path() for file in file_dialog.open_multiple_finish(result) if file
        ]
        if files:
          self._open_import_dialog(files)
      except GLib.GError:
        pass

    select_files()

  def on_create_library_action(self, *_args) -> None:
    """Creates a new library in a selected directory"""

    def select_dir() -> None:
      logger.debug("Showing library creation dialog")
      dialog = Gtk.FileDialog(
        default_filter=Gtk.FileFilter(mime_types=["inode/directory"])
      )
      dialog.select_folder(self, None, on_selected_dir)

    def on_selected_dir(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      try:
        _dir = file_dialog.select_folder_finish(result)
        if _dir is not None:
          dir_path = _dir.get_path()
          if not dir_path:
            return
          try:
            library_path = LibraryManager.new_library(Path(dir_path))
          except Exception:
            logger.exception("Failed to create library: %s")
            self.show_toast(_("Failed to create library"), 3)
            return
          self.open_library(str(library_path))
      except GLib.GError:
        pass

    select_dir()

  def on_register_tag_action(self, *_args) -> None:
    """Shows tag registration dialog"""
    TagRegistrationDialog().present(self)

  def _open_import_dialog(self, files: list[str]) -> None:
    if LibraryManager.current_library is None:
      self.show_toast(_("Open a library before importing files"), 3)
      return

    dialog = ImportDialog(
      files,
      self._on_import_dialog_confirmed,
    )
    dialog.present(self)

  def _on_import_dialog_confirmed(
    self, files: list[str], import_with_lyrics: bool, elrc_prefix: str, move: bool
  ) -> None:
    self.import_files_to_library(
      files,
      move=move,
      import_with_lyrics=import_with_lyrics,
      elrc_prefix=elrc_prefix,
    )

  ##############################

  ############### Drag and drop handlers ###############
  @Gtk.Template.Callback()
  def dnd_area_autohide(self, revealer: Gtk.Revealer, *_args) -> None:
    """Sets the DND area to be invisible

    Parameters
    ----------
    revealer : Gtk.Revealer
        revealer to hide
    """
    revealer.set_visible(revealer.props.child_revealed)

  def _on_drag_enter(self, *_args) -> None:
    if self.navigation_view.get_visible_page() == self.library_nav_page:
      logger.debug("Showing DND area")
      self.dnd_area_revealer.set_visible(True)
      self.dnd_area_revealer.set_reveal_child(True)
      self.dnd_area_revealer.set_can_target(True)
      return Gdk.DragAction.COPY
    self.drop_target.reject()

  def _on_drag_leave(self, *_args) -> None:
    logger.debug("Hiding DND area")
    self.dnd_area_revealer.set_reveal_child(False)
    self.dnd_area_revealer.set_can_target(False)

  def _on_drag_drop(
    self, _drop_target: Gtk.DropTarget, value: GObject.Value, *_args
  ) -> None:
    files = [file.get_path() for file in value.get_files()]
    logger.info("DND recieved files: %s\n", "\n".join(files))
    if LibraryManager.current_library is not None:
      self.import_files_to_library(files)
    else:
      self.show_toast(_("Open a library before importing files"), 3)
    self._on_drag_leave()

  def _on_drag_accept(self, _target: Gtk.DropTarget, drop: Gdk.Drop, *_args) -> bool:
    def verify_files_valid(drop: Gdk.Drop, task: Gio.Task, *_args) -> bool:
      try:
        files = drop.read_value_finish(task).get_files()
      except GLib.GError:
        self.drop_target.reject()
        self._on_drag_leave()
        return False

      if not any(
        (
          Path(file.get_path()).suffix
          in [
            ".ogg",
            ".flac",
            ".opus",
            ".mp3",
            ".wav",
            ".m4a",
            ".aac",
            ".AAC",
          ]
        )
        for file in files
      ):
        self.drop_target.reject()
        self._on_drag_leave()

      for file in files:
        path = file.get_path()
        if Path(path).is_dir():
          logger.warning("'%s' is a directory, rejecting DND", path)
          self.drop_target.reject()
          self._on_drag_leave()

    drop.read_value_async(Gdk.FileList, 0, None, verify_files_valid)
    return True

  ##############################

  def open_library(self, path: str) -> bool:
    if not LibraryManager.open_library(path):
      self.show_toast(_("Selected folder is not a Chronograph Library"))
      return False

    Schema.set("root.state.library.last-library", path)
    self._load_library_tracks()
    self.build_sidebar()
    self.state = WindowState.LIBRARY
    return True

  def _load_library_tracks(self) -> None:
    if LibraryManager.current_library is None:
      self.library.clear()
      return

    self.library.clear()
    cards: list[SongCardModel] = []

    for track in LibraryManager.list_tracks():
      media_path = LibraryManager.track_path(track.track_uuid, track.format)
      if media_path.exists() and parse_file(media_path) is not None:
        cards.append(SongCardModel(media_path, track.track_uuid))

    if cards:
      self.library.add_cards(cards)
    else:
      self.library.card_filter_model.notify("n-items")

  def import_files_to_library(
    self,
    files: list[str],
    *,
    move: bool = False,
    import_with_lyrics: bool = True,
    elrc_prefix: str = "",
  ) -> None:
    if LibraryManager.current_library is None:
      self.show_toast(_("Open a library to import files"))
      return

    if self._import_task is not None:
      self.show_toast(_("Import already in progress"))
      return

    pending_files = [Path(file) for file in files if file]
    if not pending_files:
      self.show_toast(_("No supported files were imported"))
      return

    self._import_dialog = ImportingDialog(len(pending_files))
    self._import_dialog.present(self)

    self._import_task = AsyncTask(
      LibraryManager.import_files_async,
      pending_files,
      move,
      do_use_progress=True,
      do_use_cancellable=False,
    )

    def on_progress(task: AsyncTask, *_args) -> None:
      if self._import_dialog is None:
        return
      progress = task.props.progress
      imported_count = min(
        len(pending_files), max(0, round(progress * len(pending_files)))
      )
      self._import_dialog.set_progress(progress, imported_count)

    def on_done(_task, imported: list[tuple[Path, str, str]]) -> None:
      self._import_task = None
      if self._import_dialog is not None:
        self._import_dialog.close()
        self._import_dialog = None

      if not imported:
        self.show_toast(_("No supported files were imported"))
        return

      cards: list[SongCardModel] = []
      for src_path, track_uuid, track_format in imported:
        self._import_track_lyrics(
          track_uuid,
          src_path,
          import_with_lyrics,
          elrc_prefix,
        )
        media_path = LibraryManager.track_path(track_uuid, track_format)
        if media_path.exists():
          cards.append(SongCardModel(media_path, track_uuid))

      if cards:
        self.library.add_cards(cards)
      else:
        self.library.card_filter_model.notify("n-items")

      self.show_toast(
        ngettext(
          "Imported {} track",
          "Imported {} tracks",
          len(imported),
        ).format(len(imported))
      )

    def on_error(_task, error: Exception) -> None:
      self._import_task = None
      if self._import_dialog is not None:
        self._import_dialog.close()
        self._import_dialog = None
      logger.error("Import failed: %s", error)
      self.show_toast(_("Import failed"))

    self._import_task.connect("notify::progress", on_progress)
    self._import_task.connect("task-done", on_done)
    self._import_task.connect("error", on_error)
    self._import_task.start()

  def _import_track_lyrics(
    self,
    track_uuid: str,
    source_path: Path,
    import_with_lyrics: bool,
    elrc_prefix: str,
  ) -> None:
    if not import_with_lyrics:
      return

    lyric_path = source_path.with_suffix(".lrc")
    self._import_lyrics_from_path(track_uuid, lyric_path, "lrc")

    elrc_prefix = elrc_prefix.strip()
    if not elrc_prefix:
      return

    prefixed_path = source_path.with_name(f"{elrc_prefix}{source_path.stem}.lrc")
    self._import_lyrics_from_path(track_uuid, prefixed_path, "elrc")

  def _import_lyrics_from_path(
    self, track_uuid: str, lyric_path: Path, fmt: str
  ) -> None:
    if not lyric_path.exists():
      return
    try:
      content = lyric_path.read_text(encoding="utf-8")
    except Exception as exc:
      logger.warning("Failed to read lyrics from '%s': %s", lyric_path, exc)
      return
    try:
      save_track_lyric(track_uuid, fmt, content)
    except Exception as exc:
      logger.warning("Failed to import lyrics from '%s': %s", lyric_path, exc)

  @Gtk.Template.Callback()
  def _on_sidebar_tag_selected(self, _list_box, row: Gtk.ListBoxRow) -> None:
    if row is None or row.get_child() is None:
      self.active_tag_filter = None
      self.library.filter.changed(Gtk.FilterChange.DIFFERENT)

  @Gtk.Template.Callback()
  def _on_sidebar_tag_activated(self, _list_box, row: Gtk.ListBoxRow) -> None:
    if row is None:
      return
    child = row.get_child()
    if child is None:
      return
    tag = child.tag
    if self.active_tag_filter == tag:
      self.sidebar.unselect_row(row)
      return
    self.active_tag_filter = tag
    self.library.filter.changed(Gtk.FilterChange.DIFFERENT)

  @Gtk.Template.Callback()
  def on_search_changed(self, *_args) -> None:
    """Calls `self.library.filter_func` to filter the library based on the search entry text"""
    self.library.filter.changed(Gtk.FilterChange.DIFFERENT)

  @Gtk.Template.Callback()
  def on_proceed_bulk_delete_button_clicked(self, *_args) -> None:
    deleted = self.library.bulk_delete_selected()
    self.enable_bulk_delete_button.set_active(False)
    self.show_toast(_("Deleted {n} files").format(n=deleted))

  def is_bulk_delete_mode(self) -> bool:
    return self.enable_bulk_delete_button.get_active()

  @Gtk.Template.Callback()
  def _on_bulk_delete_mode_toggled(self, *_args) -> None:
    self.library.set_bulk_delete_mode(self.enable_bulk_delete_button.get_active())

  ################# Quick Editor ###############

  def on_open_quick_editor_action(self, *_args) -> None:
    """Opens the quick editor dialog"""
    if Schema.get("root.settings.general.reset-quick-editor"):
      self.quick_edit_text_view.set_buffer(Gtk.TextBuffer.new())
    logger.debug("Showing quick editor")
    self.quick_edit_dialog.present(self)

  @Gtk.Template.Callback()
  def copy_quick_editor_text(self, *_args) -> None:
    """Exports `self.quick_editor` text to clipboard"""
    text = self.quick_edit_text_view.get_buffer().get_text(
      start=self.quick_edit_text_view.get_buffer().get_start_iter(),
      end=self.quick_edit_text_view.get_buffer().get_end_iter(),
      include_hidden_chars=False,
    )
    clipboard = Gdk.Display().get_default().get_clipboard()
    clipboard.set(text)
    logger.info("Quick Editor text copied")
    self.quck_editor_toast_overlay.add_toast(Adw.Toast(title=_("Copied successfully")))

  #################

  def on_sort_type_action(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
    """Changes the sorting state of the library in GSchema and updates the library

    Parameters
    ----------
    action : Gio.SimpleAction
        Action that was triggered
    state : GLib.Variant
        New state of the action ("a-z", "z-a")
    """
    action.set_state(state)
    self.sort_state = str(state).strip("'")
    self.library.sorter.changed(Gtk.SorterChange.DIFFERENT)
    logger.debug("Sort state set to: %s", self.sort_state)
    Schema.set("root.state.library.sorting", self.sort_state)

  def enter_sync_mode(self, card_model: SongCardModel) -> None:
    """Enters sync mode for the given song card

    Parameters
    ----------
    card_model : SongCardModel
      Card model with all necessary data for sync page
    """
    if Schema.get("root.settings.syncing.sync-type") == "lrc":
      logger.info(
        "Entering sync mode for '%s -- %s' in LRC syncing format",
        card_model.title_display,
        card_model.artist_display,
      )
      sync_nav_page = LRCSyncPage(card_model)
      self.navigation_view.push(sync_nav_page)
    elif Schema.get("root.settings.syncing.sync-type") == "wbw":
      sync_nav_page = WBWSyncPage(card_model)
      self.navigation_view.push(sync_nav_page)

  def show_toast(
    self,
    msg: str,
    timeout: int = 5,
    button_label: Optional[str] = None,
    button_callback: Optional[Callable] = None,
  ) -> None:
    """Shows a toast with the given message and optional button

    Parameters
    ----------
    msg : str
      Message to show in the toast
    timeout : int, optional
      Timeout for the toast in seconds, defaults to 5
    button_label : str, optional
      Label for the button, if any
    button_callback : Callable, optional
      Callback for the button, if any
    """
    toast = Adw.Toast(title=msg, timeout=timeout, use_markup=False)
    if button_label and button_callback:
      toast.set_button_label(button_label)
      toast.connect("button-clicked", button_callback)
    self.toast_overlay.add_toast(toast)
    logger.debug(
      "Shown toast with:\nmsg: %s\nbutton_label: %s\ntimeout: %s",
      msg,
      button_label,
      timeout,
    )

  def _on_filter_state(self, _obj, _pspec) -> None:
    nn = self.lookup_action("filter_none").get_state().get_boolean()
    pp = self.lookup_action("filter_plain").get_state().get_boolean()
    ll = self.lookup_action("filter_lrc").get_state().get_boolean()
    ee = self.lookup_action("filter_elrc").get_state().get_boolean()
    Schema.set("root.state.library.filter", encode_filter_schema(nn, pp, ll, ee))
    self.library.filter.changed(Gtk.FilterChange.DIFFERENT)

  ############### WindowState related methods ###############
  @GObject.Property()
  def state(self) -> WindowState:
    """Current state of the window"""
    return self._state

  @state.setter
  def state(self, value: Union[WindowState, int]) -> None:
    if isinstance(value, WindowState):
      self._state = value
    else:
      self._state = WindowState(value)

  def _state_changed(self, *_args) -> None:
    state = self._state
    is_no_library = state == WindowState.NO_LIBRARY
    self.window_state_stack.set_visible_child(
      self.no_library_view if is_no_library else self.navigation_view
    )

    self.left_buttons_revealer.set_reveal_child(state == WindowState.LIBRARY)
    self.right_buttons_revealer.set_reveal_child(state == WindowState.LIBRARY)

    if is_no_library:
      self.sidebar.select_row(None)
    logger.debug("Window state was set to: %s", self.state)
