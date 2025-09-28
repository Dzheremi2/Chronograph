# TODO: Implement TTML (Timed Text Markup Language) support
# TODO: Implement LRC metatags support

import os
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from chronograph.internal import Constants, Schema
from chronograph.ui.dialogs.preferences import ChronographPreferences
from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
from chronograph.ui.sync_pages.wbw_sync_page import WBWSyncPage
from chronograph.ui.widgets.saved_location import SavedLocation
from chronograph.ui.widgets.song_card import SongCard
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable
from chronograph.utils.file_parsers import parse_dir, parse_files
from chronograph.utils.invalidators import invalidate_filter, invalidate_sort
from chronograph.utils.miscellaneous import get_common_directory
from dgutils.decorators import singleton

gtc = Gtk.Template.Child  # pylint: disable=invalid-name
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


# pylint: disable=inconsistent-return-statements, comparison-with-callable
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
    reparse_dir_button: Gtk.Button = gtc()
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
        self._state: Optional[WindowState] = None
        self.connect("notify::state", self._state_changed)

        # Connect the search entry to the search bar
        self.search_bar.connect_entry(self.search_entry)

        # Set sort and filter functions for the library
        self.library.set_sort_func(invalidate_sort)
        self.library.set_filter_func(invalidate_filter)
        self.library_list.set_sort_func(invalidate_sort)
        self.library_list.set_filter_func(invalidate_filter)

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
        if not ChronographPreferences.opened:
            preferences = ChronographPreferences()
            preferences.present(self)
            logger.debug("Showing preferences")

    def load_files(self, paths: tuple[str]) -> bool:
        """Loads files into the library

        Parameters
        ----------
        paths : tuple[str]
            Paths to files to load

        Returns
        -------
        bool
            Returns True if files were loaded
        """

        def __songcard_idle(
            file: Union[FileID3, FileVorbis, FileMP4, FileUntaggable],
        ) -> None:
            song_card = SongCard(file)
            self.library.append(song_card)
            self.library_list.append(song_card.get_list_mode())
            song_card.get_parent().set_focusable(False)
            logger.debug(
                "SongCard for song '%s -- %s' was added",
                song_card.title_display,
                song_card.artist_display,
            )

        mutagen_files = parse_files(paths)
        if not mutagen_files:
            return False
        for mutagen_file in mutagen_files:
            if isinstance(mutagen_file, (FileID3, FileVorbis, FileMP4, FileUntaggable)):
                GLib.idle_add(__songcard_idle, mutagen_file)
        self.open_source_button.set_icon_name("open-source-symbolic")
        if path := get_common_directory(paths):
            Schema.set("root.state.library.session", path)
        return True

    def open_directory(self, path: str) -> None:
        """Open a directory and load its files, updating window state"""
        logger.info("Opening '%s' directory", path)

        files = parse_dir(path)
        mutagen_files = parse_files(files)

        self.clean_library()
        Schema.set("root.state.library.session", path)

        self.add_dir_to_saves_button.set_visible(
            path not in [pin["path"] for pin in Constants.CACHE["pins"]]
        )

        if mutagen_files:
            self.load_files(files)
            self.state = WindowState.LOADED_DIR
        else:
            self.state = WindowState.EMPTY_DIR

    def open_files(self, paths: list[str]) -> None:
        """Open provided files and update window state"""
        logger.info("Opening files:\n%s", "\n".join(paths))
        if not self._state == WindowState.LOADED_FILES:
            self.clean_library()
        if self.load_files(tuple(paths)):
            self.state = WindowState.LOADED_FILES
        else:
            self.state = WindowState.EMPTY
        Schema.set("root.state.library.session", "None")

    @Gtk.Template.Callback()
    def clean_files_button_clicked(self, *_args) -> None:
        self.clean_library()
        self.state = WindowState.EMPTY
        logger.info("Library cleaned")

    ############### Actions for opening files and directories ###############
    def on_select_dir_action(self, *_args) -> None:
        """Selects a directory to open in the library"""

        def __select_dir() -> None:
            logger.debug("Showing directory selection dialog")
            dialog = Gtk.FileDialog(
                default_filter=Gtk.FileFilter(mime_types=["inode/directory"])
            )
            self.open_source_button.set_child(Adw.Spinner())
            dialog.select_folder(self, None, __on_selected_dir)

        def __on_selected_dir(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
            try:
                _dir = file_dialog.select_folder_finish(result)
                if _dir is not None:
                    dir_path = _dir.get_path()
                    self.open_directory(dir_path)
            except GLib.GError:
                pass
            finally:
                self.open_source_button.set_icon_name("open-source-symbolic")

        __select_dir()

    def on_select_files_action(self, *_args) -> None:
        """Selects files to open in the library"""

        def __select_files(*_args) -> None:
            logger.debug("Showing files selection dialog")
            dialog = Gtk.FileDialog(
                default_filter=Gtk.FileFilter(mime_types=MIME_TYPES)
            )
            self.open_source_button.set_child(Adw.Spinner())
            dialog.open_multiple(self, None, __on_select_files)

        def __on_select_files(file_dialog: Gtk.FileDialog, result: Gio.Task) -> None:
            try:
                files = [
                    file.get_path() for file in file_dialog.open_multiple_finish(result)
                ]
                if files is not None:
                    self.open_files(files)
            except GLib.GError:
                pass
            finally:
                self.open_source_button.set_icon_name("open-source-symbolic")

        __select_files()

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
        self.open_files(files)
        self._on_drag_leave()

    def _on_drag_accept(self, _target: Gtk.DropTarget, drop: Gdk.Drop, *_args) -> bool:
        def verify_files_valid(drop: Gdk.Drop, task: Gio.Task, *_args) -> bool:
            try:
                files = drop.read_value_finish(task).get_files()
            except GLib.GError:
                self.drop_target.reject()
                self._on_drag_leave()
                return False

            for file in files:
                path = file.get_path()
                if os.path.isdir(path):
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

    def clean_library(self, *_args) -> None:
        """Remove all `SongCard`s from the library"""
        logger.info("Removing all cards from library")
        self.library.remove_all()
        self.library_list.remove_all()

    @Gtk.Template.Callback()
    def on_search_changed(self, *_args) -> None:
        """Calls `self.library.filter_func` to filter the library based on the search entry text"""
        self.library.invalidate_filter()
        self.library_list.invalidate_filter()

    @Gtk.Template.Callback()
    def on_reparse_dir_button_clicked(self, *_args) -> None:
        """Re-parses the current directory in the library"""
        if self.state in (WindowState.LOADED_DIR, WindowState.EMPTY_DIR):
            logger.debug("Re-parsing current directory")
            if Schema.get("root.state.library.session") != "None":
                self.open_directory(Schema.get("root.state.library.session"))
            else:
                self.set_property("state", WindowState.EMPTY)

    @Gtk.Template.Callback()
    def on_add_dir_to_saves_button_clicked(self, *_args) -> None:
        """Adds the current directory to the saved locations in the sidebar"""
        if self.state in (WindowState.LOADED_DIR, WindowState.EMPTY_DIR):
            if Schema.get("root.state.library.session") != "None":
                dir_path = Schema.get("root.state.library.session") + "/"
                if dir_path not in [pin["path"] for pin in Constants.CACHE["pins"]]:
                    Constants.CACHE["pins"].append(
                        {"path": dir_path, "name": Path(dir_path).name}
                    )
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
        self.quck_editor_toast_overlay.add_toast(
            Adw.Toast(title=_("Copied successfully"))
        )

    #################

    def on_sort_type_action(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
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

    def on_view_type_action(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
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

    def enter_sync_mode(
        self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
    ) -> None:
        """Enters sync mode for the given song card

        Parameters
        ----------
        card : SongCard
            Song card to enter sync mode for
        """
        if Schema.get("root.settings.syncing.sync-type") == "lrc":
            logger.info(
                "Entering sync mode for '%s -- %s' in LRC syncing format",
                card.title,
                card.artist,
            )
            sync_nav_page = LRCSyncPage(card, file)
            self.navigation_view.push(sync_nav_page)
        elif Schema.get("root.settings.syncing.sync-type") == "wbw":
            sync_nav_page = WBWSyncPage(card, file)
            self.navigation_view.push(sync_nav_page)

    def show_toast(
        self,
        msg: str,
        timeout: int = 5,
        button_label: str = None,
        button_callback: Callable = None,
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
            self.library_scrolled_window.get_child().get_child()
            != self.no_source_opened
            and self.library_scrolled_window.get_child().get_child()
            != self.empty_directory
            and self.is_visible()
        ):
            if self.get_width() <= 564:
                self.library_scrolled_window.set_child(self.library_list)
                Schema.set("root.state.library.view", "l")
                Constants.APP.lookup_action("view_type").set_state(
                    GLib.Variant.new_string("l")
                )
            else:
                self.library_scrolled_window.set_child(self.library)
                Schema.set("root.state.library.view", "g")
                Constants.APP.lookup_action("view_type").set_state(
                    GLib.Variant.new_string("g")
                )

    ############### WindowState related methods ###############
    @GObject.Property()
    def state(self) -> WindowState:  # pylint: disable=method-hidden
        """Current state of the window"""
        return self._state

    @state.setter
    def state(self, value: WindowState) -> None:
        self._state = value

    def _state_changed(self, *_args) -> None:
        def __select_saved_location() -> None:
            try:
                for row in self.sidebar:  # pylint: disable=not-an-iterable
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
                self.clean_library()
            case WindowState.EMPTY_DIR:
                self.library_scrolled_window.set_child(self.empty_directory)
                self.right_buttons_revealer.set_reveal_child(True)
                self.left_buttons_revealer.set_reveal_child(False)
                self.clean_files_button.set_visible(False)
                self.clean_library()
                __select_saved_location()
            case WindowState.LOADED_DIR:
                match Schema.get("root.state.library.view"):
                    case "g":
                        self.library_scrolled_window.set_child(self.library)
                    case "l":
                        self.library_scrolled_window.set_child(self.library_list)
                self.right_buttons_revealer.set_reveal_child(True)
                self.left_buttons_revealer.set_reveal_child(True)
                self.clean_files_button.set_visible(False)
                self.clean_library()
                __select_saved_location()
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
