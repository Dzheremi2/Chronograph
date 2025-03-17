from enum import Enum
from typing import Literal

from gi.repository import Adw, Gio, GLib, Gtk, GObject

from chronograph.ui.SongCard import SongCard  # type: ignore

class WindowState(Enum):
    """Enum for window states

    ::

        EMPTY -> "No dir nor files opened"
        EMPTY_DIR -> "Opened an empty dir"
        LOADED_DIR -> "Opened a non-empty dir"
        LOADED_FILES -> "Opened a bunch of files separately from the dir "
    """

    EMPTY: Literal[0]
    EMPTY_DIR: Literal[1]
    LOADED_DIR: Literal[2]
    LOADED_FILES: Literal[3]

class ChronographWindow(Adw.ApplicationWindow):
    """App window class"""

    # Status pages
    no_source_opened: Adw.StatusPage
    empty_directory: Adw.StatusPage
    search_lrclib_status_page: Adw.StatusPage
    search_lrclib_collapsed_status_page: Adw.StatusPage
    lrclib_window_nothing_found_status: Adw.StatusPage
    lrclib_window_collapsed_nothing_found_status: Adw.StatusPage
    no_saves_found_status: Adw.StatusPage

    # Library view widgets
    help_overlay: Gtk.ShortcutsWindow
    toast_overlay: Adw.ToastOverlay
    navigation_view: Adw.NavigationView
    library_nav_page: Adw.NavigationPage
    overlay_split_view: Adw.OverlaySplitView
    sidebar_window: Gtk.ScrolledWindow
    sidebar: Gtk.ListBox
    open_source_button: Gtk.MenuButton
    left_buttons_revealer: Gtk.Revealer
    search_bar: Gtk.SearchBar
    search_entry: Gtk.SearchEntry
    right_buttons_revealer: Gtk.Revealer
    reparse_dir_button: Gtk.Button
    add_dir_to_saves_button: Gtk.Button
    clean_files_button: Gtk.Button
    library_overlay: Gtk.Overlay
    library_scrolled_window: Gtk.ScrolledWindow
    library: Gtk.FlowBox
    library_list: Gtk.ListBox

    # Quick Editor
    quick_edit_dialog: Adw.Dialog
    quck_editor_toast_overlay: Adw.ToastOverlay
    quick_edit_text_view: Gtk.TextView
    quick_edit_copy_button: Gtk.Button

    # Syncing page widgets
    sync_navigation_page: Adw.NavigationPage
    controls: Gtk.MediaControls
    controls_shrinked: Gtk.MediaControls
    sync_page_cover: Gtk.Image
    sync_page_title: Gtk.Inscription
    sync_page_artist: Gtk.Inscription
    toggle_repeat_button: Gtk.ToggleButton
    sync_line_button: Gtk.Button
    replay_line_button: Gtk.Button
    rew100_button: Gtk.Button
    forw100_button: Gtk.Button
    export_lyrics_button: Gtk.MenuButton
    info_button: Gtk.Button
    sync_lines: Gtk.ListBox
    add_line_button: Gtk.Button

    # LRClib window dialog widgets
    lrclib_window: Adw.Dialog
    lrclib_window_toast_overlay: Adw.ToastOverlay
    lrclib_window_main_clamp: Adw.Clamp
    lrclib_window_title_entry: Gtk.Entry
    lrclib_window_artist_entry: Gtk.Entry
    lrclib_window_results_list_window: Gtk.ScrolledWindow
    lrclib_window_results_list: Gtk.ListBox
    lrclib_window_synced_lyrics_text_view: Gtk.TextView
    lrclib_window_plain_lyrics_text_view: Gtk.TextView
    lrclib_window_collapsed_navigation_view: Adw.NavigationView
    lrclib_window_collapsed_lyrics_page: Adw.NavigationPage
    lrclib_window_collapsed_results_list_window: Gtk.ScrolledWindow
    lrclib_window_collapsed_results_list: Gtk.ListBox

    # Lrclib manual publishing dialog
    lrclib_manual_dialog: Adw.Dialog
    lrclib_manual_toast_overlay: Adw.ToastOverlay
    lrclib_manual_title_entry: Adw.EntryRow
    lrclib_manual_artist_entry: Adw.EntryRow
    lrclib_manual_album_entry: Adw.EntryRow
    lrclib_manual_duration_entry: Adw.EntryRow
    lrclib_manual_publish_button: Gtk.Button

    sort_state: str
    view_state: str

    loaded_card: SongCard
    _state: WindowState

    def on_toggle_sidebar_action(self, *_args) -> None: ...
    def on_toggle_search_action(self, *_args) -> None: ...
    def on_select_dir_action(self, *_args) -> None: ...
    def filtering(self, child: Gtk.FlowBoxChild) -> bool: ...
    def filtering_list(self, child: Adw.ActionRow) -> bool: ...
    def sorting(self, child1: Gtk.FlowBoxChild, child2: Gtk.FlowBoxChild) -> int: ...
    def sorting_list(self, child1: Adw.ActionRow, child2: Adw.ActionRow) -> int: ...
    def on_search_changed(self, entry: Gtk.SearchEntry) -> None: ...
    def on_sort_changed(self, *_args) -> None: ...
    def on_view_type_action(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None: ...
    def on_append_line_action(self, *_args): ...
    def on_remove_selected_line_action(self, *_args): ...
    def on_prepend_selected_line_action(self, *_args): ...
    def on_append_selected_line_action(self, *_args): ...
    def on_sync_line_action(self, *_args) -> None: ...
    def on_replay_line_action(self, *_args) -> None: ...
    def on_100ms_rew_action(self, *_args) -> None: ...
    def on_100ms_forw_action(self, *_args) -> None: ...
    def on_show_file_info_action(self, *_args) -> None: ...
    def on_import_from_clipboard_action(self, *_args) -> None: ...
    def on_import_from_file_action(self, *_args) -> None: ...
    def on_import_from_lrclib_action(self, *_args) -> None: ...
    def on_search_lrclib_action(self, *_args) -> None: ...
    def set_lyrics(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None: ...
    def on_import_lyrics_lrclib_synced_action(self, *_args) -> None: ...
    def on_import_lyrics_lrclib_plain_action(self, *_args) -> None: ...
    def on_export_to_file_action(self, *_args) -> None: ...
    def on_export_to_clipboard_action(self, *_args) -> None: ...
    def on_export_to_lrclib_action(self, *_args) -> None: ...
    def manual_publish(self, *_args) -> None: ...
    def on_show_preferences_action(self, *args) -> None: ...
    def on_open_quick_editor_action(self, *_args) -> None: ...
    def copy_quick_editor_text(self, *_args) -> None: ...
    def on_timestamp_changed(self, media_stream: Gtk.MediaStream, *_args) -> None: ...
    def toggle_repeat(self, *_args) -> None: ...
    def build_sidebar(self, *_args) -> None: ...
    def load_save(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None: ...
    def toggle_list_view(self, *_args) -> None: ...
    @GObject.Property
    def state(self) -> WindowState: ...
    @state.setter
    def state(self, new_state: WindowState) -> None: ...
    def update_win_state(self, *_args) -> None: ...
