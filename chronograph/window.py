# DELAYED: Add GStreamer based player with music speed control
# TODO: Reimplement syncing page as a separate class generatable for every song
# TODO: Reimplement LRC support
# TODO: Implement eLRC (Enchanted LRC) support
# TODO: Implement TTML (Timed Text Markup Language) support
# TODO: Implement different syncing pages variants for different syncing formats (LRC, eLRC, TTML, etc.)
# TODO: Implement logger
# TODO: Reimplement List View mode

import os
from enum import Enum
from typing import Callable, Optional, Union

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from chronograph.internal import Constants, Schema
from chronograph.ui.dialogs.preferences import ChronographPreferences
from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
from chronograph.ui.widgets.saved_location import SavedLocation
from chronograph.ui.widgets.song_card import SongCard
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable
from chronograph.utils.invalidators import invalidate_filter, invalidate_sort
from chronograph.utils.miscellaneous import get_common_directory
from chronograph.utils.parsers import parse_dir, parse_files

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
@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/window.ui")
class ChronographWindow(Adw.ApplicationWindow):
    """App window class"""

    __gtype_name__ = "ChronographWindow"

    # Status pages
    no_source_opened: Adw.StatusPage = Gtk.Template.Child()
    empty_directory: Adw.StatusPage = Gtk.Template.Child()
    no_saves_found_status: Adw.StatusPage = Gtk.Template.Child()

    # Library view widgets
    help_overlay: Gtk.ShortcutsWindow = Gtk.Template.Child()
    dnd_area_revealer: Gtk.Revealer = Gtk.Template.Child()
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    library_nav_page: Adw.NavigationPage = Gtk.Template.Child()
    overlay_split_view: Adw.OverlaySplitView = Gtk.Template.Child()
    sidebar_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    sidebar: Gtk.ListBox = Gtk.Template.Child()
    open_source_button: Gtk.MenuButton = Gtk.Template.Child()
    left_buttons_revealer: Gtk.Revealer = Gtk.Template.Child()
    search_bar: Gtk.SearchBar = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    right_buttons_revealer: Gtk.Revealer = Gtk.Template.Child()
    reparse_dir_button: Gtk.Button = Gtk.Template.Child()
    add_dir_to_saves_button: Gtk.Button = Gtk.Template.Child()
    clean_files_button: Gtk.Button = Gtk.Template.Child()
    library_overlay: Gtk.Overlay = Gtk.Template.Child()
    library_scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    library: Gtk.FlowBox = Gtk.Template.Child()

    # Quick Editor
    quick_edit_dialog: Adw.Dialog = Gtk.Template.Child()
    quck_editor_toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    quick_edit_text_view: Gtk.TextView = Gtk.Template.Child()
    quick_edit_copy_button: Gtk.Button = Gtk.Template.Child()

    sort_state: str = Schema.sorting
    view_state: str = Schema.STATEFULL.get_string("view")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Setting keybindings help overlay
        self.set_help_overlay(self.help_overlay)

        # Apply devel window decorations
        if Constants.APP_ID.endswith(".Devel"):
            self.add_css_class("devel")

        # Create a WindowState property for automatic window UI state updates
        self._state: Optional[WindowState] = None
        self.connect("notify::state", self._state_changed)

        # Connect the search entry to the search bar
        self.search_bar.connect_entry(self.search_entry)

        # Set sort and filter functions for the library
        self.library.set_sort_func(invalidate_sort)
        self.library.set_filter_func(invalidate_filter)

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
        self.sidebar.remove_all()
        for pin in Constants.CACHE["pins"]:
            self.sidebar.append(SavedLocation(pin["path"], pin["name"]))
        # TODO: remove useless item amount check. Use `placeholder` property of listbox instead
        if not self.sidebar.get_row_at_index(0):
            self.sidebar_window.set_child(self.no_saves_found_status)
        else:
            self.sidebar_window.set_child(self.sidebar)

    def on_toggle_sidebar_action(self, *_args) -> None:
        """Toggle sidebar visibility"""
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

    def on_show_preferences_action(self, *_args) -> None:
        """Shows the preferences dialog"""
        if not ChronographPreferences.opened:
            preferences = ChronographPreferences()
            preferences.present(self)

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
            song_card.get_parent().set_focusable(False)

        mutagen_files = parse_files(paths)
        if not mutagen_files:
            return False
        for mutagen_file in mutagen_files:
            if isinstance(mutagen_file, (FileID3, FileVorbis, FileMP4, FileUntaggable)):
                GLib.idle_add(__songcard_idle, mutagen_file)
        self.open_source_button.set_icon_name("open-source-symbolic")
        if path := get_common_directory(paths):
            Schema.STATEFULL.set_string("session", path)
        return True

    def open_directory(self, path: str) -> None:
        """Open a directory and load its files, updating window state"""

        files = parse_dir(path)
        mutagen_files = parse_files(files)

        self.clean_library()
        Schema.STATEFULL.set_string("session", path)

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

        self.clean_library()
        if self.load_files(tuple(paths)):
            self.state = WindowState.LOADED_FILES
        else:
            self.state = WindowState.EMPTY
        Schema.STATEFULL.set_string("session", "None")

    @Gtk.Template.Callback()
    def clean_files_button_clicked(self, *_args) -> None:
        self.clean_library()
        self.state = WindowState.EMPTY

    ############### Actions for opening files and directories ###############
    def on_select_dir_action(self, *_args) -> None:
        """Selects a directory to open in the library"""

        def __select_dir() -> None:
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
            self.dnd_area_revealer.set_visible(True)
            self.dnd_area_revealer.set_reveal_child(True)
            self.dnd_area_revealer.set_can_target(True)
            return Gdk.DragAction.COPY
        self.drop_target.reject()

    def _on_drag_leave(self, *_args) -> None:
        self.dnd_area_revealer.set_reveal_child(False)
        self.dnd_area_revealer.set_can_target(False)

    def _on_drag_leave(self, *_args) -> None:
        self.dnd_area_revealer.set_reveal_child(False)
        self.dnd_area_revealer.set_can_target(False)

    def _on_drag_drop(
        self, _drop_target: Gtk.DropTarget, value: GObject.Value, *_args
    ) -> None:
        files = [file.get_path() for file in value.get_files()]
        self.open_files(files)
        self._on_drag_leave()

    def _on_drag_accept(self, _target: Gtk.DropTarget, drop: Gdk.Drop, *_args) -> bool:
        def __verify_files_valid(drop: Gdk.Drop, task: Gio.Task, *_args) -> bool:
            try:
                files = drop.read_value_finish(task).get_files()
            except GLib.GError:
                self.drop_target.reject()
                self._on_drag_leave()
                return False

            for file in files:
                path = file.get_path()
                if os.path.isdir(path):
                    self.drop_target.reject()
                    self._on_drag_leave()

        drop.read_value_async(Gdk.FileList, 0, None, __verify_files_valid)
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
            row.get_child().load()
        except AttributeError:
            pass

    def clean_library(self, *_args) -> None:
        """Remove all `SongCard`s from the library"""
        self.library.remove_all()

    @Gtk.Template.Callback()
    def on_search_changed(self, *_args) -> None:
        """Calls `self.library.filter_func` to filter the library based on the search entry text"""
        self.library.invalidate_filter()

    @Gtk.Template.Callback()
    def on_reparse_dir_button_clicked(self, *_args) -> None:
        """Re-parses the current directory in the library"""
        if self.state in (WindowState.LOADED_DIR, WindowState.EMPTY_DIR):
            if Schema.session != "None":
                self.open_directory(Schema.session)
            else:
                self.set_property("state", WindowState.EMPTY)

    @Gtk.Template.Callback()
    def on_add_dir_to_saves_button_clicked(self, *_args) -> None:
        """Adds the current directory to the saved locations in the sidebar"""
        if self.state in (WindowState.LOADED_DIR, WindowState.EMPTY_DIR):
            if Schema.session != "None":
                dir_path = Schema.session
                if dir_path not in [pin["path"] for pin in Constants.CACHE["pins"]]:
                    Constants.CACHE["pins"].append(
                        {"path": dir_path, "name": os.path.basename(dir_path)}
                    )
                    self.add_dir_to_saves_button.set_visible(False)
                    self.build_sidebar()

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
        Schema.STATEFULL.set_string("sorting", self.sort_state)

    def enter_sync_mode(
        self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
    ) -> None:
        """Enters sync mode for the given song card

        Parameters
        ----------
        card : SongCard
            Song card to enter sync mode for
        """
        if Schema.default_format == "lrc":
            sync_nav_page = LRCSyncPage(card, file)
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
            for row in self.sidebar:  # pylint: disable=not-an-iterable
                if row.get_child().path == Schema.session:
                    self.sidebar.select_row(row)
                    return

        state = self._state
        self.open_source_button.set_icon_name("open-source-symbolic")
        match state:
            case WindowState.EMPTY:
                self.library_scrolled_window.set_child(self.no_source_opened)
                self.right_buttons_revealer.set_reveal_child(False)
                self.left_buttons_revealer.set_reveal_child(False)
                self.clean_files_button.set_visible(False)
                Schema.STATEFULL.set_string("session", "None")
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
                # TODO:
                # match Schema.STATEFULL.get_string("view"):
                #     case "g":
                self.library_scrolled_window.set_child(self.library)
                #     case "l":
                #         self.library_scrolled_window.set_child(self.library_list)
                self.right_buttons_revealer.set_reveal_child(True)
                self.left_buttons_revealer.set_reveal_child(True)
                self.clean_files_button.set_visible(False)
                self.clean_library()
                __select_saved_location()
            case WindowState.LOADED_FILES:
                # match shared.state_schema.get_string("view"):
                #     case "g":
                self.library_scrolled_window.set_child(self.library)
                #     case "l":
                #         self.library_scrolled_window.set_child(self.library_list)
                Schema.STATEFULL.set_string("session", "None")
                self.right_buttons_revealer.set_reveal_child(False)
                self.clean_files_button.set_visible(True)
                self.sidebar.select_row(None)
