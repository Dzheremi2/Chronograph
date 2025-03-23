import os
import pathlib
import re
import threading
from enum import Enum

import requests
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from chronograph import shared
from chronograph.ui.LrclibTrack import LrclibTrack
from chronograph.ui.Preferences import ChronographPreferences
from chronograph.ui.SavedLocation import SavedLocation
from chronograph.ui.SongCard import SongCard
from chronograph.ui.SyncLine import SyncLine
from chronograph.utils.caching import save_location
from chronograph.utils.export_data import export_clipboard, export_file
from chronograph.utils.file_untaggable import FileUntaggable
from chronograph.utils.parsers import (
    clipboard_parser,
    dir_parser,
    parse_files,
    string_parser,
    sync_lines_parser,
    timing_parser,
)
from chronograph.utils.publish import do_publish
from chronograph.utils.select_data import select_dir, select_files, select_lyrics_file


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


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/window.ui")
class ChronographWindow(Adw.ApplicationWindow):
    """App window class"""

    __gtype_name__ = "ChronographWindow"

    # Status pages
    no_source_opened: Adw.StatusPage = Gtk.Template.Child()
    empty_directory: Adw.StatusPage = Gtk.Template.Child()
    search_lrclib_status_page: Adw.StatusPage = Gtk.Template.Child()
    search_lrclib_collapsed_status_page: Adw.StatusPage = Gtk.Template.Child()
    lrclib_window_nothing_found_status: Adw.StatusPage = Gtk.Template.Child()
    lrclib_window_collapsed_nothing_found_status: Adw.StatusPage = Gtk.Template.Child()
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
    library_list: Gtk.ListBox = Gtk.Template.Child()

    # Quick Editor
    quick_edit_dialog: Adw.Dialog = Gtk.Template.Child()
    quck_editor_toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    quick_edit_text_view: Gtk.TextView = Gtk.Template.Child()
    quick_edit_copy_button: Gtk.Button = Gtk.Template.Child()

    # Syncing page widgets
    sync_navigation_page: Adw.NavigationPage = Gtk.Template.Child()
    controls: Gtk.MediaControls = Gtk.Template.Child()
    controls_shrinked: Gtk.MediaControls = Gtk.Template.Child()
    sync_page_cover: Gtk.Image = Gtk.Template.Child()
    sync_page_title: Gtk.Inscription = Gtk.Template.Child()
    sync_page_artist: Gtk.Inscription = Gtk.Template.Child()
    toggle_repeat_button: Gtk.ToggleButton = Gtk.Template.Child()
    sync_line_button: Gtk.Button = Gtk.Template.Child()
    replay_line_button: Gtk.Button = Gtk.Template.Child()
    rew100_button: Gtk.Button = Gtk.Template.Child()
    forw100_button: Gtk.Button = Gtk.Template.Child()
    export_lyrics_button: Gtk.MenuButton = Gtk.Template.Child()
    sync_page_metadata_editor_button_box: Gtk.Box = Gtk.Template.Child()
    sync_page_metadata_editor_button_shrinked_box: Gtk.Box = Gtk.Template.Child()
    info_button: Gtk.Button = Gtk.Template.Child()
    sync_lines: Gtk.ListBox = Gtk.Template.Child()
    add_line_button: Gtk.Button = Gtk.Template.Child()

    # LRClib window dialog widgets
    lrclib_window: Adw.Dialog = Gtk.Template.Child()
    lrclib_window_toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    lrclib_window_main_clamp: Adw.Clamp = Gtk.Template.Child()
    lrclib_window_title_entry: Gtk.Entry = Gtk.Template.Child()
    lrclib_window_artist_entry: Gtk.Entry = Gtk.Template.Child()
    lrclib_window_results_list_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    lrclib_window_results_list: Gtk.ListBox = Gtk.Template.Child()
    lrclib_window_synced_lyrics_text_view: Gtk.TextView = Gtk.Template.Child()
    lrclib_window_plain_lyrics_text_view: Gtk.TextView = Gtk.Template.Child()
    lrclib_window_collapsed_navigation_view: Adw.NavigationView = Gtk.Template.Child()
    lrclib_window_collapsed_lyrics_page: Adw.NavigationPage = Gtk.Template.Child()
    lrclib_window_collapsed_results_list_window: Gtk.ScrolledWindow = (
        Gtk.Template.Child()
    )
    lrclib_window_collapsed_results_list: Gtk.ListBox = Gtk.Template.Child()

    # Lrclib manual publishing dialog
    lrclib_manual_dialog: Adw.Dialog = Gtk.Template.Child()
    lrclib_manual_toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    lrclib_manual_title_entry: Adw.EntryRow = Gtk.Template.Child()
    lrclib_manual_artist_entry: Adw.EntryRow = Gtk.Template.Child()
    lrclib_manual_album_entry: Adw.EntryRow = Gtk.Template.Child()
    lrclib_manual_duration_entry: Adw.EntryRow = Gtk.Template.Child()
    lrclib_manual_publish_button: Gtk.Button = Gtk.Template.Child()

    sort_state: str = shared.state_schema.get_string("sorting")
    view_state: str = shared.state_schema.get_string("view")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.loaded_card: SongCard = None
        self._state: WindowState = None

        if shared.APP_ID.endswith("Devel"):
            self.add_css_class("devel")

        self.set_help_overlay(self.help_overlay)
        self.search_bar.connect_entry(self.search_entry)
        self.library.set_filter_func(self.filtering)
        self.library_list.set_filter_func(self.filtering_list)
        self.library.set_sort_func(self.sorting)
        self.library_list.set_sort_func(self.sorting_list)
        self.reparse_dir_button.connect(
            "clicked",
            lambda *_: dir_parser(shared.state_schema.get_string("opened-dir")[:-1]),
        )
        self.add_dir_to_saves_button.connect("clicked", save_location)
        self.connect("notify::state", self.update_win_state)

        self.drop_target = Gtk.DropTarget(
            actions=Gdk.DragAction.COPY,
            formats=Gdk.ContentFormats.new_for_gtype(Gdk.FileList),
        )
        self.drop_target.connect("accept", self.on_drag_accept)
        self.drop_target.connect("enter", self.on_drag_enter)
        self.drop_target.connect("leave", self.on_drag_leave)
        self.drop_target.connect("drop", self.on_drag_drop)
        self.add_controller(self.drop_target)

        if self.library.get_child_at_index(0) is None:
            self.library_scrolled_window.set_child(self.no_source_opened)
        self.build_sidebar()

    def on_toggle_sidebar_action(self, *_args) -> None:
        """Toggles sidebar of `self`"""
        if self.navigation_view.get_visible_page() is self.library_nav_page:
            self.overlay_split_view.set_show_sidebar(
                not self.overlay_split_view.get_show_sidebar()
            )

    @Gtk.Template.Callback()
    def reset_sync_editor(self, *_args) -> None:
        self.sync_lines.remove_all()
        shared.selected_line = None
        self.controls.get_media_stream().stream_ended()
        self.controls_shrinked.get_media_stream().stream_ended()
        self.toggle_repeat_button.set_active(False)

    def on_toggle_search_action(self, *_args) -> None:
        """Toggles search field of `self`"""
        if self.navigation_view.get_visible_page() == self.library_nav_page:
            search_bar = self.search_bar
            search_entry = self.search_entry
        else:
            return

        search_bar.set_search_mode(not (search_mode := search_bar.get_search_mode()))

        if not search_mode:
            self.set_focus(search_entry)

        search_entry.set_text("")

    def on_select_dir_action(self, *_args) -> None:
        """Creates directory selection dialog for adding Songs to `self.library`"""
        select_dir()

    def on_select_files_action(self, *_args) -> None:
        """Create files selection dialog for adding songs to `self.library`"""
        select_files()

    def filtering(self, child: Gtk.FlowBoxChild) -> bool:
        """Technical function for `Gtk.FlowBox.invalidate_filter` working

        Parameters
        ----------
        child : Gtk.FlowBoxChild
            Child for determining if it should be filtered or not

        Returns
        ----------
        bool
            `True` if child should be displayed, `False` if not
        """
        try:
            card: SongCard = child.get_child()
            text = self.search_entry.get_text().lower()
            filtered = text != "" and not (
                text in card.title.lower() or text in card.artist.lower()
            )
            return not filtered
        except AttributeError:
            pass

    def filtering_list(self, row: Adw.ActionRow) -> bool:
        """Technical function for `Gtk.ListBox.invalidate_filter` working
        Parameters
        ----------
        row : Adw.ActionRow
            Row for determining if it should be filtered or not

        Returns
        ----------
        bool
            `True` if row should be displayed, `False` if not
        """
        try:
            text = self.search_entry.get_text().lower()
            filtered = text != "" and not (
                text in row.get_title().lower() or text in row.get_subtitle().lower()
            )
            return not filtered
        except AttributeError:
            pass

    def sorting(self, child1: Gtk.FlowBoxChild, child2: Gtk.FlowBoxChild) -> int:
        """Technical function for `Gtk.FlowBox.invalidate_sort` working

        Parameters
        ----------
        child1 : Gtk.FlowBoxChild
            1st child for comparison
        child2 : Gtk.FlowBoxChild
            2nd child for comparison

        Returns
        ----------
        int
            `-1` if `child1` should be before `child2`, `1` if `child1` should be after `child2`
        """
        order = None
        if shared.win.sort_state == "a-z":
            order = False
        elif shared.win.sort_state == "z-a":
            order = True
        return ((child1.get_child().title > child2.get_child().title) ^ order) * 2 - 1

    def sorting_list(self, child1: Adw.ActionRow, child2: Adw.ActionRow) -> int:
        """Technical function for `Gtk.ListBox.invalidate_sort` working

        Parameters
        ----------
        child1 : Adw.ActionRow
            1st child for comparison
        child2 : Adw.ActionRow
            2nd child for comparison

        Returns
        ----------
        int
            `-1` if `child1` should be before `child2`, `1` if `child1` should be after `child2`
        """
        order = None
        if shared.win.sort_state == "a-z":
            order = False
        elif shared.win.sort_state == "z-a":
            order = True
        return ((child1.get_title() > child2.get_title()) ^ order) * 2 - 1

    @Gtk.Template.Callback()
    def on_search_changed(self, *_args) -> None:
        """Invalidates filter for `self.library`"""
        if self.library_scrolled_window.get_child().get_child() == self.library:
            self.library.invalidate_filter()
        else:
            self.library_list.invalidate_filter()

    def on_sorting_type_action(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        """Sets sorting state for `self.library` and invalidates sorting

        Parameters
        ----------
        action : Gio.SimpleAction
            Action which triggered this function
        state : GLib.Variant
            Current sorting state
        """
        action.set_state(state)
        self.sort_state = str(state).strip("'")
        self.library.invalidate_sort()
        self.library_list.invalidate_sort()
        shared.state_schema.set_string("sorting", self.sort_state)

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
        shared.state_schema.set_string("view", self.view_state)

    def on_show_file_info_action(self, *_args) -> None:
        """Creates dialog with information about selected file"""
        self.loaded_card.gen_box_dialog()

    def on_append_line_action(self, *_args) -> None:
        """Appends new `SyncLine` to `self.sync_lines`"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            self.sync_lines.append(SyncLine())

    def on_remove_selected_line_action(self, *_args) -> None:
        """Removes selected `SyncLine` from `self.sync_lines`"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            lines = []
            for line in self.sync_lines:
                lines.append(line)
            index = lines.index(shared.selected_line)
            self.sync_lines.remove(shared.selected_line)
            self.sync_lines.get_row_at_index(index).grab_focus()

    def on_prepend_selected_line_action(self, *_args) -> None:
        """Prepends new `SyncLine` before selected `SyncLine` in `self.sync_lines`"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            if shared.selected_line in self.sync_lines:
                childs = []
                for child in self.sync_lines:
                    childs.append(child)
                index = childs.index(shared.selected_line)
                if index > 0:
                    self.sync_lines.insert(SyncLine(), index)
                elif index == 0:
                    self.sync_lines.prepend(SyncLine())

    def on_append_selected_line_action(self, *_args) -> None:
        """Appends new `SyncLine` after selected `SyncLine` in `self.sync_lines`"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            if shared.selected_line in self.sync_lines:
                childs = []
                for child in self.sync_lines:
                    childs.append(child)
                index = childs.index(shared.selected_line)
                self.sync_lines.insert(SyncLine(), index + 1)

    def on_sync_line_action(self, *_args) -> None:
        """Syncs selected `SyncLine` with current media stream timestamp"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            pattern = r"\[([^\[\]]+)\] "
            timestamp = self.controls.get_media_stream().get_timestamp() // 1000
            if shared.schema.get_boolean("precise-milliseconds"):
                timestamp = f"[{timestamp // 60000:02d}:{(timestamp % 60000) // 1000:02d}.{timestamp % 1000:03d}] "
            else:
                milliseconds = f"{timestamp % 1000:03d}"
                timestamp = f"[{timestamp // 60000:02d}:{(timestamp % 60000) // 1000:02d}.{milliseconds[:-1]}] "
                del milliseconds
            if shared.selected_line in self.sync_lines:
                childs = []
                for child in self.sync_lines:
                    childs.append(child)
                index = childs.index(shared.selected_line)
            else:
                pass

            if re.search(pattern, shared.selected_line.get_text()) is None:
                shared.selected_line.set_text(
                    timestamp + shared.selected_line.get_text()
                )
            else:
                replacement = rf"{timestamp}"
                shared.selected_line.set_text(
                    re.sub(pattern, replacement, shared.selected_line.get_text())
                )

            if (indexed_row := self.sync_lines.get_row_at_index(index + 1)) is not None:
                indexed_row.grab_focus()
            else:
                pass

    def on_replay_line_action(self, *_args) -> None:
        """Replays selected `SyncLine` for its timestamp"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            self.controls.get_media_stream().seek(
                timing_parser(shared.selected_line.get_text()) * 1000
            )

    def on_100ms_rew_action(self, *_args) -> None:
        """Rewinds media stream for 100ms from selected `SyncLine` timestamp and resync itself timestamp"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            pattern = r"\[([^\[\]]+)\]"
            if (
                line_timestamp_prefix := timing_parser(shared.selected_line.get_text())
            ) >= 100:
                timestamp = line_timestamp_prefix - 100
                if shared.schema.get_boolean("precise-milliseconds"):
                    new_timestamp = f"[{timestamp // 60000:02d}:{(timestamp % 60000) // 1000:02d}.{timestamp % 1000:03d}]"
                else:
                    milliseconds = f"{timestamp % 1000:03d}"
                    new_timestamp = f"[{timestamp // 60000:02d}:{(timestamp % 60000) // 1000:02d}.{milliseconds[:-1]}]"
                    del milliseconds
                replacement = rf"{new_timestamp}"
                shared.selected_line.set_text(
                    re.sub(pattern, replacement, shared.selected_line.get_text())
                )
                self.controls.get_media_stream().seek(timestamp * 1000)
            else:
                if shared.schema.get_boolean("precise-milliseconds"):
                    replacement = rf"[00:00.000]"
                else:
                    replacement = rf"[00:00.00]"
                shared.selected_line.set_text(
                    re.sub(pattern, replacement, shared.selected_line.get_text())
                )
                self.controls.get_media_stream().seek(0)

    def on_100ms_forw_action(self, *_args) -> None:
        """Forwards media stream for 100ms from selected `SyncLine` timestamp and resync itself timestamp"""
        if self.navigation_view.get_visible_page() is self.sync_navigation_page:
            timestamp = timing_parser(shared.selected_line.get_text()) + 100
            if shared.schema.get_boolean("precise-milliseconds"):
                new_timestamp = f"[{timestamp // 60000:02d}:{(timestamp % 60000) // 1000:02d}.{timestamp % 1000:03d}]"
            else:
                milliseconds = f"{timestamp % 1000:03d}"
                new_timestamp = f"[{timestamp // 60000:02d}:{(timestamp % 60000) // 1000:02d}.{milliseconds[:-1]}]"
                del milliseconds
            shared.selected_line.set_text(
                re.sub(
                    r"\[([^\[\]]+)\]",
                    rf"{new_timestamp}",
                    shared.selected_line.get_text(),
                )
            )
            self.controls.get_media_stream().seek(timestamp * 1000)

    def on_import_from_clipboard_action(self, *_args) -> None:
        """Imports text from clipboard to `self.sync_lines`"""
        clipboard_parser()

    def on_import_from_file_action(self, *_args) -> None:
        """Imports text from file to `self.sync_lines`"""
        select_lyrics_file()

    def on_import_from_lrclib_action(self, *_args) -> None:
        """Presents `self.lrclib_window` dialog"""
        self.lrclib_window_artist_entry.set_buffer(Gtk.EntryBuffer())
        self.lrclib_window_title_entry.set_buffer(Gtk.EntryBuffer())
        self.lrclib_window_results_list.remove_all()
        self.lrclib_window_results_list_window.set_child(self.search_lrclib_status_page)
        self.lrclib_window_synced_lyrics_text_view.set_buffer(Gtk.TextBuffer.new())
        self.lrclib_window_plain_lyrics_text_view.set_buffer(Gtk.TextBuffer.new())
        self.lrclib_window_collapsed_results_list.remove_all()
        self.lrclib_window_collapsed_results_list_window.set_child(
            self.search_lrclib_collapsed_status_page
        )
        self.lrclib_window.present(self)

    def on_search_lrclib_action(self, *_args) -> None:
        """Parses LRclib for tracks with Title and Artist from `self.lrclib_window_title_entry` and `self.lrclib_window_artist_entry`"""
        request: requests.Response = requests.get(
            url="https://lrclib.net/api/search",
            params={
                "track_name": self.lrclib_window_title_entry.get_text(),
                "artist_name": self.lrclib_window_artist_entry.get_text(),
            },
        )
        print(request.url)
        result = request.json()
        self.lrclib_window_results_list.remove_all()
        self.lrclib_window_collapsed_results_list.remove_all()
        if len(result) > 0:
            for item in result:
                self.lrclib_window_results_list.append(
                    LrclibTrack(
                        title=item["trackName"],
                        artist=item["artistName"],
                        tooltip=(
                            item["trackName"],
                            item["artistName"],
                            item["duration"],
                            item["albumName"],
                            item["instrumental"],
                        ),
                        synced=item["syncedLyrics"],
                        plain=item["plainLyrics"],
                    )
                )
                self.lrclib_window_collapsed_results_list.append(
                    LrclibTrack(
                        title=item["trackName"],
                        artist=item["artistName"],
                        tooltip=(
                            item["trackName"],
                            item["artistName"],
                            item["duration"],
                            item["albumName"],
                            item["instrumental"],
                        ),
                        synced=item["syncedLyrics"],
                        plain=item["plainLyrics"],
                    )
                )
            self.lrclib_window_results_list_window.set_child(
                self.lrclib_window_results_list
            )
            self.lrclib_window_collapsed_results_list_window.set_child(
                self.lrclib_window_collapsed_results_list
            )
        else:
            self.lrclib_window_results_list_window.set_child(
                self.lrclib_window_nothing_found_status
            )
            self.lrclib_window_collapsed_results_list_window.set_child(
                self.lrclib_window_collapsed_nothing_found_status
            )

    @Gtk.Template.Callback()
    def set_lyrics(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        """Triggers `chronograph.ui.LrclibTrack.set_lyrics`

        Parameters
        ----------
        _listbox : Gtk.ListBox
            garbage parameter
        row : Gtk.ListBoxRow
            `Gtk.ListBoxRow` to claim `LrclibTrack` from
        """
        row.get_child().set_lyrics()

    def on_import_lyrics_lrclib_synced_action(self, *_args) -> None:
        """Import synced lyrics from LRCLib to `self.sync_lines`"""
        string_parser(
            self.lrclib_window_synced_lyrics_text_view.get_buffer().get_text(
                start=self.lrclib_window_synced_lyrics_text_view.get_buffer().get_start_iter(),
                end=self.lrclib_window_synced_lyrics_text_view.get_buffer().get_end_iter(),
                include_hidden_chars=False,
            )
        )
        self.lrclib_window.close()

    def on_import_lyrics_lrclib_plain_action(self, *_args) -> None:
        """Import plain lyrics from LRCLib to `self.sync_lines`"""
        string_parser(
            self.lrclib_window_plain_lyrics_text_view.get_buffer().get_text(
                start=self.lrclib_window_plain_lyrics_text_view.get_buffer().get_start_iter(),
                end=self.lrclib_window_plain_lyrics_text_view.get_buffer().get_end_iter(),
                include_hidden_chars=False,
            )
        )
        self.lrclib_window.close()

    def on_export_to_file_action(self, *_args) -> None:
        """Exports current `self.sync_lines` lyrics to file"""
        export_file(sync_lines_parser())

    def on_export_to_clipboard_action(self, *_args) -> None:
        """Exports current `self.sync_lines` lyrics to clipbaord"""
        export_clipboard(sync_lines_parser())

    def on_export_to_lrclib_action(self, *_args) -> None:
        """Publishes synced lyrics to LRClib"""
        if type(self.loaded_card._file) is FileUntaggable:
            self.lrclib_manual_title_entry.set_text("")
            self.lrclib_manual_artist_entry.set_text("")
            self.lrclib_manual_album_entry.set_text("")
            self.lrclib_manual_duration_entry.set_text("")
            self.lrclib_manual_dialog.present(self)
        else:
            if (
                self.loaded_card._file.title is None
                or self.loaded_card._file.title == ""
                or self.loaded_card._file.artist is None
                or self.loaded_card._file.artist == ""
                or self.loaded_card._file.album is None
                or self.loaded_card._file.album == ""
            ):
                self.toast_overlay.add_toast(
                    Adw.Toast(
                        title=_(
                            "Some of Title, Artist and/or Album fields are Unknown!"
                        )
                    )
                )
                self.export_lyrics_button.set_icon_name("export-to-symbolic")
                raise AttributeError(
                    'Some of Title, Artist and/or Album fields are "Unknown"'
                )

            thread = threading.Thread(
                target=do_publish,
                args=[
                    self.loaded_card._file.title,
                    self.loaded_card._file.artist,
                    self.loaded_card._file.album,
                    self.loaded_card._file.duration,
                    sync_lines_parser(),
                ],
            )
            thread.daemon = True
            thread.start()
            shared.win.export_lyrics_button.set_child(Adw.Spinner())

    @Gtk.Template.Callback()
    def manual_publish(self, *_args) -> None:
        """Manual publishing to the LRClib"""
        if (
            self.lrclib_manual_title_entry.get_text() != ""
            and self.lrclib_manual_artist_entry.get_text() != ""
            and self.lrclib_manual_album_entry.get_text() != ""
            and self.lrclib_manual_duration_entry.get_text() != ""
        ):
            thread = threading.Thread(
                target=do_publish,
                args=[
                    self.lrclib_manual_title_entry.get_text(),
                    self.lrclib_manual_artist_entry.get_text(),
                    self.lrclib_manual_album_entry.get_text(),
                    int(self.lrclib_manual_duration_entry.get_text()),
                    sync_lines_parser(),
                ],
            )
            thread.daemon = True
            thread.start()
            self.lrclib_manual_publish_button.set_child(Adw.Spinner())
        else:
            self.lrclib_manual_toast_overlay.add_toast(
                Adw.Toast(title=_("Some of entries are empty"))
            )

    def on_show_preferences_action(self, *args) -> None:
        """Shows preferences dialog"""
        if ChronographPreferences.opened:
            return
        preferences = ChronographPreferences()
        preferences.present(shared.win)

    def on_open_quick_editor_action(self, *_args) -> None:
        """Shows `self.quick_editor`"""
        if shared.schema.get_boolean("reset-quick-editor"):
            self.quick_edit_text_view.set_buffer(Gtk.TextBuffer.new())
        self.quick_edit_dialog.present(self)

    @Gtk.Template.Callback()
    def copy_quick_editor_text(self, *_args) -> None:
        """Exports `self.quick_editor` text to clipboard"""
        export_clipboard(
            self.quick_edit_text_view.get_buffer().get_text(
                start=self.quick_edit_text_view.get_buffer().get_start_iter(),
                end=self.quick_edit_text_view.get_buffer().get_end_iter(),
                include_hidden_chars=False,
            )
        )
        self.quck_editor_toast_overlay.add_toast(
            Adw.Toast(title=_("Copied successfully"))
        )

    def on_timestamp_changed(self, media_stream: Gtk.MediaStream, *_args) -> None:
        """Higlights line with timestamp larger that current and smaller that next

        Parameters
        ----------
        media_stream : Gtk.MediaStream
            `Gtk.MediaStream` to get timestamp from
        """
        attributes = Pango.AttrList().from_string("0 -1 weight ultrabold")
        try:
            lines = []
            timestamps = []
            for line in self.sync_lines:
                line.set_attributes(None)
                if (timing := timing_parser(line.get_text())) is not None:
                    lines.append(line)
                    timestamps.append(timing)
                else:
                    break
            timestamp = media_stream.get_timestamp() // 1000
            for i in range(len(timestamps)):
                if timestamp > timestamps[i] and timestamp < timestamps[i + 1]:
                    lines[i].set_attributes(attributes)
                    break
                elif timestamp >= timestamps[-1]:
                    lines[-1].set_attributes(attributes)
        except (TypeError, AttributeError, IndexError):
            pass

    @Gtk.Template.Callback()
    def toggle_repeat(self, *_args) -> None:
        """Toggles repeat mode in player"""
        if self.toggle_repeat_button.get_active():
            self.controls.get_media_stream().set_loop(True)
            self.controls_shrinked.get_media_stream().set_loop(True)
        else:
            self.controls.get_media_stream().set_loop(False)
            self.controls_shrinked.get_media_stream().set_loop(False)

    def build_sidebar(self, *_args) -> None:
        """Fills saves sidebar with save rows"""
        if len(shared.cache["pins"]) != 0:
            self.sidebar.remove_all()
            entries: list = []
            for entry in shared.cache["pins"]:
                entries.append(entry)
            entries = sorted(entries, key=lambda x: x["name"].lower())
            for entry in entries:
                self.sidebar.append(
                    SavedLocation(path=entry["path"], name=entry["name"])
                )
            self.sidebar_window.set_child(self.sidebar)
        else:
            self.sidebar_window.set_child(self.no_saves_found_status)

    @Gtk.Template.Callback()
    def load_save(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        """Launching `chronograph.utils.parsers.dir_parser` for saved path

        Parameters
        ----------
        _listbox : Gtk.ListBox
            ListBox which emited this method
        row : Gtk.ListBoxRow
            Row to get SavedLocation from
        """
        for pin in shared.cache["pins"]:
            if pin["path"] == row.get_child().path:
                if row.get_child().path != shared.state_schema.get_string("opened-dir"):
                    if self.overlay_split_view.get_collapsed():
                        self.overlay_split_view.set_show_sidebar(
                            not self.overlay_split_view.get_show_sidebar()
                        )
                    dir_parser(pin["path"][:-1])
                    break

    @Gtk.Template.Callback()
    def toggle_list_view(self, *_args) -> None:
        if shared.schema.get_boolean("auto-list-view") and (
            self.library_scrolled_window.get_child().get_child()
            != self.no_source_opened
            and self.library_scrolled_window.get_child().get_child()
            != self.empty_directory
        ):
            if self.get_width() <= 564:
                self.library_scrolled_window.set_child(self.library_list)
                shared.state_schema.set_string("view", "l")
                shared.app.lookup_action("view_type").set_state(
                    GLib.Variant.new_string("l")
                )
            else:
                self.library_scrolled_window.set_child(self.library)
                shared.state_schema.set_string("view", "g")
                shared.app.lookup_action("view_type").set_state(
                    GLib.Variant.new_string("g")
                )

    @Gtk.Template.Callback()
    def clean_library(self, *_args) -> None:
        """Removes all song cards and sets self state to `EMPTY`"""
        self.library.remove_all()
        self.library_list.remove_all()
        self.state = WindowState.EMPTY

    @Gtk.Template.Callback()
    def dnd_area_autohide(self, revealer: Gtk.Revealer, *_args) -> None:
        """Sets the DND area to be invisible

        Parameters
        ----------
        revealer : Gtk.Revealer
            revealer to hide
        """
        revealer.set_visible(revealer.props.child_revealed)

    def on_drag_accept(self, target: Gtk.DropTarget, drop: Gdk.Drop, *_args) -> bool:
        """Trigger when DND action is about to happen and runs files validity checker

        Parameters
        ----------
        target : Gtk.DropTarget
            DropTarget callbacked this method
        drop : Gdk.Drop
            Drop itsefl

        Returns
        -------
        bool
        """
        drop.read_value_async(Gdk.FileList, 0, None, self.verify_files_valid)
        return True

    def verify_files_valid(self, drop: Gdk.Drop, task: Gio.Task, *_args) -> bool:
        """Denies DropTarget if droppable files contains invalid files

        Parameters
        ----------
        drop : Gdk.Drop
            Drop itself
        task : Gio.Task
            Task to get files from

        Returns
        -------
        bool
            False if error in reading files occured
        """
        try:
            files = drop.read_value_finish(task).get_files()
        except GLib.GError:
            self.drop_target.reject()
            self.on_drag_leave()
            return False

        for file in files:
            path = file.get_path()
            if os.path.isdir(path):
                self.drop_target.reject()
                self.on_drag_leave()

    def on_drag_enter(self, *_args) -> None:
        """Shows DropTarget area to user

        Returns
        -------
        Gdk.DragAction
            COPY type of Dragging
        """
        if self.navigation_view.get_visible_page() != self.sync_navigation_page:
            self.dnd_area_revealer.set_visible(True)
            self.dnd_area_revealer.set_reveal_child(True)
            self.dnd_area_revealer.set_can_target(True)
            return Gdk.DragAction.COPY
        else:
            self.drop_target.reject()

    def on_drag_leave(self, *_args) -> None:
        """Hides DropTarget area from the user"""
        self.dnd_area_revealer.set_reveal_child(False)
        self.dnd_area_revealer.set_can_target(False)

    def on_drag_drop(
        self, drop_target: Gtk.DropTarget, value: GObject.Value, *_args
    ) -> None:
        """Adds dropped files to the `self.library`

        Parameters
        ----------
        drop_target : Gtk.DropTarget
            DropTarget itself
        value : GObject.Value
            A group of files
        """
        files = value.get_files()

        if self.state == WindowState.LOADED_DIR:
            shared.win.library.remove_all()
            shared.win.library_list.remove_all()

        if parse_files([f.get_path() for f in files]):
            self.state = WindowState.LOADED_FILES
        else:
            self.state = WindowState.EMPTY
        self.on_drag_leave()

    @Gtk.Template.Callback()
    def on_edit_song_metadata(self, *_args) -> None:
        self.loaded_card.open_metadata_editor()

    @GObject.Property
    def state(self) -> WindowState:
        return self._state

    @state.setter
    def state(self, new_state: WindowState) -> None:
        self._state = new_state

    def update_win_state(self, *_args) -> None:
        """Changes state of `self` depending on current `self.state` prop value"""
        self.open_source_button.set_icon_name("open-source-symbolic")
        match self.state:
            case WindowState.EMPTY:
                self.library_scrolled_window.set_child(self.no_source_opened)
                self.right_buttons_revealer.set_reveal_child(False)
                self.left_buttons_revealer.set_reveal_child(False)
                self.clean_files_button.set_visible(False)
                shared.state_schema.set_string("opened-dir", "None")
            case WindowState.EMPTY_DIR:
                self.library_scrolled_window.set_child(self.empty_directory)
                self.right_buttons_revealer.set_reveal_child(False)
                self.left_buttons_revealer.set_reveal_child(False)
                self.clean_files_button.set_visible(False)
                shared.state_schema.set_string("opened-dir", "None")
            case WindowState.LOADED_DIR:
                match shared.state_schema.get_string("view"):
                    case "g":
                        self.library_scrolled_window.set_child(self.library)
                    case "l":
                        self.library_scrolled_window.set_child(self.library_list)
                self.right_buttons_revealer.set_reveal_child(True)
                self.left_buttons_revealer.set_reveal_child(True)
                self.clean_files_button.set_visible(False)
            case WindowState.LOADED_FILES:
                match shared.state_schema.get_string("view"):
                    case "g":
                        self.library_scrolled_window.set_child(self.library)
                    case "l":
                        self.library_scrolled_window.set_child(self.library_list)
                shared.state_schema.set_string("opened-dir", "None")
                self.right_buttons_revealer.set_reveal_child(False)
                self.clean_files_button.set_visible(True)
