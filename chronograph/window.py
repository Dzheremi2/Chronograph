# TODO: Implement TTML (Timed Text Markup Language) support
# TODO: Implement LRC metatags support

from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from chronograph.internal import Constants, Schema
from chronograph.ui.dialogs.preferences import ChronographPreferences
from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
from chronograph.ui.sync_pages.wbw_sync_page import WBWSyncPage
from chronograph.ui.widgets.saved_location import SavedLocation
from chronograph.utils.file_backend import LibraryModel, SongCardModel
from chronograph.utils.invalidators import (
  invalidate_filter_flowbox,
  invalidate_filter_listbox,
  invalidate_sort_flowbox,
  invalidate_sort_listbox,
)
from chronograph.utils.miscellaneous import (
  decode_filter_schema,
  encode_filter_schema,
)
from dgutils.decorators import singleton

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


class WindowState(Enum):
  """Enum for window states

  ::

      EMPTY -> "No dir nor files opened"
      EMPTY_DIR -> "Opened an empty dir"
      LOADED_DIR -> "Opened a non-empty dir"
      LOADED_FILES -> "Opened a bunch of files separately from the dir"
  """

  EMPTY = 0
  EMPTY_DIR = 1
  LOADED_DIR = 2
  LOADED_FILES = 3


@singleton
@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/window.ui")
class ChronographWindow(Adw.ApplicationWindow):
  """App window class"""

  __gtype_name__ = "ChronographWindow"

  # Status pages
  no_source_opened: Adw.StatusPage = gtc()
  empty_directory: Adw.StatusPage = gtc()
  no_saves_found_status: Adw.StatusPage = gtc()

  # Library view widgets
  dnd_area_revealer: Gtk.Revealer = gtc()
  toast_overlay: Adw.ToastOverlay = gtc()
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
  add_dir_to_saves_button: Gtk.Button = gtc()
  clean_files_button: Gtk.Button = gtc()
  library_overlay: Gtk.Overlay = gtc()
  library_scrolled_window: Gtk.ScrolledWindow = gtc()
  library: Gtk.FlowBox = gtc()

  # Quick Editor
  quick_edit_dialog: Adw.Dialog = gtc()
  quck_editor_toast_overlay: Adw.ToastOverlay = gtc()
  quick_edit_text_view: Gtk.TextView = gtc()
  quick_edit_copy_button: Gtk.Button = gtc()

  filter_none: bool = GObject.Property(type=bool, default=True)
  filter_plain: bool = GObject.Property(type=bool, default=True)
  filter_lrc: bool = GObject.Property(type=bool, default=True)
  filter_elrc: bool = GObject.Property(type=bool, default=True)

  sort_state: str = Schema.get("root.state.library.sorting")
  view_state: str = Schema.get("root.state.library.view")

  def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)

    logger.debug("Creating window")

    self.library_list = Gtk.ListBox(
      css_classes=("navigation-sidebar",), selection_mode=Gtk.SelectionMode.NONE
    )

    # Apply devel window decorations
    if Constants.APP_ID.endswith(".Devel"):
      logger.debug("Devel detected, enabling devel window decorations")
      self.add_css_class("devel")

    # Create a WindowState property for automatic window UI state updates
    self._state: WindowState = WindowState.EMPTY
    self.connect("notify::state", self._state_changed)

    # Connect the search entry to the search bar
    self.search_bar.connect_entry(self.search_entry)

    # Set sort and filter functions for the library
    self.library.set_sort_func(invalidate_sort_flowbox)
    self.library.set_filter_func(invalidate_filter_flowbox)
    self.library_list.set_sort_func(invalidate_sort_listbox)
    self.library_list.set_filter_func(invalidate_filter_listbox)

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

    # Building up the sidebar with saved locations
    self.build_sidebar()

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

  def build_sidebar(self) -> None:
    """Builds the sidebar with saved locations"""
    logger.debug("Building the sidebar")
    self.sidebar.remove_all()
    Constants.CACHE["pins"] = [
      pin for pin in Constants.CACHE["pins"] if Path(pin["path"]).exists()
    ]
    for pin in Constants.CACHE["pins"]:
      self.sidebar.append(SavedLocation(pin["path"], pin["name"]))
    self.sidebar.set_placeholder(self.no_saves_found_status)

  def on_toggle_sidebar_action(self, *_args) -> None:
    """Toggle sidebar visibility"""
    logger.debug("Toggling sidebar")
    if self.navigation_view.get_visible_page() is self.library_nav_page:
      self.overlay_split_view.set_show_sidebar(
        not self.overlay_split_view.get_show_sidebar()
      )

  def on_toggle_search_action(self, *_args) -> None:
    """Toggles search field of `self`"""
    if self.state in (WindowState.EMPTY, WindowState.EMPTY_DIR):
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

  @Gtk.Template.Callback()
  def clean_files_button_clicked(self, *_args) -> None:
    LibraryModel().reset_library()

  ############### Actions for opening files and directories ###############
  def on_select_dir_action(self, *_args) -> None:
    """Selects a directory to open in the library"""

    def select_dir() -> None:
      logger.debug("Showing directory selection dialog")
      dialog = Gtk.FileDialog(
        default_filter=Gtk.FileFilter(mime_types=["inode/directory"])
      )
      self.open_source_button.set_child(Adw.Spinner())
      dialog.select_folder(self, None, on_selected_dir)

    def on_selected_dir(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      try:
        _dir = file_dialog.select_folder_finish(result)
        if _dir is not None:
          dir_path = _dir.get_path()
          LibraryModel().open_dir(dir_path)
      except GLib.GError:
        pass
      finally:
        self.open_source_button.set_icon_name("open-source-symbolic")

    select_dir()

  def on_select_files_action(self, *_args) -> None:
    """Selects files to open in the library"""

    def select_files(*_args) -> None:
      logger.debug("Showing files selection dialog")
      dialog = Gtk.FileDialog(default_filter=Gtk.FileFilter(mime_types=MIME_TYPES))
      self.open_source_button.set_child(Adw.Spinner())
      dialog.open_multiple(self, None, on_select_files)

    def on_select_files(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
      try:
        files = [file.get_path() for file in file_dialog.open_multiple_finish(result)]
        if files is not None:
          LibraryModel().open_files(files)
      except GLib.GError:
        pass
      finally:
        self.open_source_button.set_icon_name("open-source-symbolic")

    select_files()

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
    LibraryModel().open_files(files)
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

  @Gtk.Template.Callback()
  def load_save(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
    """Loads a saved location from the sidebar

    Parameters
    ----------
    _list_box : Gtk.ListBox
        List box containing saved locations
    row : Gtk.ListBoxRow
        Row containing the saved location to load
    """
    try:
      if row.get_child().path[:-1] != Schema.get("root.state.library.session"):
        logger.info("Loading save '%s'", row.get_child().name)
        row.get_child().load()
    except AttributeError:
      pass

  @Gtk.Template.Callback()
  def on_search_changed(self, *_args) -> None:
    """Calls `self.library.filter_func` to filter the library based on the search entry text"""
    self.library.invalidate_filter()
    self.library_list.invalidate_filter()

  @Gtk.Template.Callback()
  def on_add_dir_to_saves_button_clicked(self, *_args) -> None:
    """Adds the current directory to the saved locations in the sidebar"""
    if (
      self.state in (WindowState.LOADED_DIR, WindowState.EMPTY_DIR)
      and Schema.get("root.state.library.session") != "None"
    ):
      dir_path = Schema.get("root.state.library.session") + "/"
      if dir_path not in [pin["path"] for pin in Constants.CACHE["pins"]]:
        Constants.CACHE["pins"].append({"path": dir_path, "name": Path(dir_path).name})
        logger.info("'%s' was added to Saves", dir_path)
        self.add_dir_to_saves_button.set_visible(False)
        self.build_sidebar()

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
    self.library.invalidate_sort()
    self.library_list.invalidate_sort()
    logger.debug("Sort state set to: %s", self.sort_state)
    Schema.set("root.state.library.sorting", self.sort_state)

  def on_view_type_action(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
    """Sets view type state for `self.library_list` and invalidates sorting

    Parameters
    ----------
    action : Gio.SimpleAction
        Action which triggered this function
    state : GLib.Variant
        Current view type state
    """
    action.set_state(state)
    self.view_state = str(state).strip("'")
    match self.view_state:
      case "g":
        self.library_scrolled_window.set_child(self.library)
      case "l":
        self.library_scrolled_window.set_child(self.library_list)
    logger.debug("View type set to: %s", self.view_state)
    Schema.set("root.state.library.view", self.view_state)

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
    toast = Adw.Toast(title=msg, timeout=timeout)
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

  @Gtk.Template.Callback()
  def toggle_list_view(self, *_args) -> None:
    if Schema.get("root.settings.general.auto-list-view") and (
      self.library_scrolled_window.get_child().get_child() != self.no_source_opened
      and self.library_scrolled_window.get_child().get_child() != self.empty_directory
      and self.is_visible()
    ):
      if self.get_width() <= 564:
        self.library_scrolled_window.set_child(self.library_list)
        Schema.set("root.state.library.view", "l")
        Constants.APP.lookup_action("view_type").set_state(GLib.Variant.new_string("l"))
      else:
        self.library_scrolled_window.set_child(self.library)
        Schema.set("root.state.library.view", "g")
        Constants.APP.lookup_action("view_type").set_state(GLib.Variant.new_string("g"))

  def _on_filter_state(self, _obj, _pspec) -> None:
    nn = self.lookup_action("filter_none").get_state().get_boolean()
    pp = self.lookup_action("filter_plain").get_state().get_boolean()
    ll = self.lookup_action("filter_lrc").get_state().get_boolean()
    ee = self.lookup_action("filter_elrc").get_state().get_boolean()
    Schema.set("root.state.library.filter", encode_filter_schema(nn, pp, ll, ee))
    self.library.invalidate_filter()
    self.library_list.invalidate_filter()

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
    def select_saved_location() -> None:
      try:
        for row in self.sidebar:
          if row.get_child().path == Schema.get("root.state.library.session") + "/":
            self.sidebar.select_row(row)
            return
      except AttributeError:
        pass

    state = self._state
    self.open_source_button.set_icon_name("open-source-symbolic")

    # Check for the "Add to Saves" button visibility
    session_path = Schema.get("root.state.library.session") + "/"
    if state in (WindowState.EMPTY_DIR, WindowState.LOADED_DIR):
      if session_path in [pin["path"] for pin in Constants.CACHE["pins"]]:
        self.add_dir_to_saves_button.set_visible(False)
      else:
        self.add_dir_to_saves_button.set_visible(True)

    match state:
      case WindowState.EMPTY:
        self.library_scrolled_window.set_child(self.no_source_opened)
        self.right_buttons_revealer.set_reveal_child(False)
        self.left_buttons_revealer.set_reveal_child(False)
        self.clean_files_button.set_visible(False)
        Schema.set("root.state.library.session", "None")
        self.sidebar.select_row(None)
      case WindowState.EMPTY_DIR:
        self.library_scrolled_window.set_child(self.empty_directory)
        self.right_buttons_revealer.set_reveal_child(True)
        self.left_buttons_revealer.set_reveal_child(False)
        self.clean_files_button.set_visible(False)
        select_saved_location()
      case WindowState.LOADED_DIR:
        match Schema.get("root.state.library.view"):
          case "g":
            self.library_scrolled_window.set_child(self.library)
          case "l":
            self.library_scrolled_window.set_child(self.library_list)
        self.right_buttons_revealer.set_reveal_child(True)
        self.left_buttons_revealer.set_reveal_child(True)
        self.clean_files_button.set_visible(False)
        select_saved_location()
      case WindowState.LOADED_FILES:
        match Schema.get("root.state.library.view"):
          case "g":
            self.library_scrolled_window.set_child(self.library)
          case "l":
            self.library_scrolled_window.set_child(self.library_list)
        Schema.set("root.state.library.session", "None")
        self.right_buttons_revealer.set_reveal_child(False)
        self.clean_files_button.set_visible(True)
        self.sidebar.select_row(None)
    logger.debug("Window state was set to: %s", self.state)
