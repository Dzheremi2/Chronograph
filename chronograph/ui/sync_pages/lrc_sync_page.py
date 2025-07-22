"""Sync page for LRC format syncing"""

import re
from typing import Union

from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.internal import Constants
from chronograph.ui.playerui import PlayerUI
from chronograph.ui.song_card import SongCard
from chronograph.utils.converter import mcs_to_timestamp, timestamp_to_mcs
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/LRCSyncPage.ui")
class LRCSyncPage(Adw.NavigationPage):
    __gtype_name__ = "LRCSyncPage"

    header_bar: Adw.HeaderBar = gtc()
    player_container: Gtk.Box = gtc()
    sync_lines_scrolled_window: Gtk.ScrolledWindow = gtc()
    sync_lines: Gtk.ListBox = gtc()
    selected_line = None

    def __init__(
        self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
    ) -> "LRCSyncPage":
        super().__init__()
        self._card: SongCard = card
        self._file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable] = file
        self._card.bind_property(
            "title", self, "title", GObject.BindingFlags.SYNC_CREATE
        )
        self._player_ui = PlayerUI(file, card)
        self._player = self._player_ui._player
        self.player_container.append(self._player_ui)

        self._setup_actions()

    def _append_end_line(self, *_args) -> None:
        self.sync_lines.append(LRCSyncLine())

    def append_line(self, *_args) -> None:
        if self.selected_line:
            for index, line in enumerate(self.sync_lines):
                if line == self.selected_line:
                    self.sync_lines.insert(sync_line := LRCSyncLine(), index + 1)
                    adj = self.sync_lines_scrolled_window.get_vadjustment()
                    value = adj.get_value()
                    sync_line.grab_focus()
                    adj.set_value(value)
                    return

    def _prepend_line(self, *_args) -> None:
        if self.selected_line:
            for index, line in enumerate(self.sync_lines):
                if line == self.selected_line:
                    try:
                        self.sync_lines.insert(LRCSyncLine(), index)
                        return
                    except IndexError:
                        self.sync_lines.prepend(LRCSyncLine())
                        return

    def _remove_line(self, *_args) -> None:
        if self.selected_line:
            self.sync_lines.remove(self.selected_line)
            self.selected_line = None

    def _sync(self, *_args) -> None:
        if self.selected_line:
            mcs = self._player.get_timestamp()
            timestamp = mcs_to_timestamp(mcs)
            pattern = re.compile(r"\[([^\[\]]+)\] ")
            if pattern.search(self.selected_line.get_text()) is None:
                self.selected_line.set_text(timestamp + self.selected_line.get_text())
            else:
                replacement = rf"{timestamp}"
                self.selected_line.set_text(
                    re.sub(pattern, replacement, self.selected_line.get_text())
                )

            for index, line in enumerate(self.sync_lines):
                if line == self.selected_line:
                    if (row := self.sync_lines.get_row_at_index(index + 1)) is not None:
                        row.grab_focus()
                        return

    def _replay(self, *_args) -> None:
        mcs = timestamp_to_mcs(self.selected_line.get_text())
        self._player.seek(mcs)

    def _seek100(self, _action, _param, mcs_seek: int) -> None:
        pattern = re.compile(r"\[([^\[\]]+)\] ")
        match = pattern.search(self.selected_line.get_text())
        if match is None:
            return
        timestamp = match[0]
        mcs = timestamp_to_mcs(timestamp) + mcs_seek
        mcs = max(mcs, 0)
        timestamp = mcs_to_timestamp(mcs)
        replacement = rf"{timestamp}"
        self.selected_line.set_text(
            re.sub(pattern, replacement, self.selected_line.get_text())
        )
        self._player.seek(mcs)

    # pylint: disable=too-many-locals, too-many-statements
    def _setup_actions(self) -> None:
        # Import actions
        _actions = Gio.SimpleActionGroup.new()
        _i_lrclib = Gio.SimpleAction.new("lrclib", None)
        _i_file = Gio.SimpleAction.new("file", None)
        _i_clipboard = Gio.SimpleAction.new("clipboard", None)
        _actions.add_action(_i_lrclib)
        _actions.add_action(_i_file)
        _actions.add_action(_i_clipboard)
        self.insert_action_group("import", _actions)

        # Export actions
        _actions = Gio.SimpleActionGroup.new()
        _e_lrclib = Gio.SimpleAction.new("lrclib", None)
        _e_file = Gio.SimpleAction.new("file", None)
        _e_clipboard = Gio.SimpleAction.new("clipboard", None)
        _actions.add_action(_e_lrclib)
        _actions.add_action(_e_file)
        _actions.add_action(_e_clipboard)
        self.insert_action_group("export", _actions)

        # Syncing actions
        _actions = Gio.SimpleActionGroup.new()
        _c_sync = Gio.SimpleAction.new("sync", None)
        _c_sync.connect("activate", self._sync)
        _c_rew100 = Gio.SimpleAction.new("rew100", None)
        _c_rew100.connect("activate", self._seek100, -100000)
        _c_forw100 = Gio.SimpleAction.new("forw100", None)
        _c_forw100.connect("activate", self._seek100, 100000)
        _c_rplay = Gio.SimpleAction.new("rplay", None)
        _c_rplay.connect("activate", self._replay)
        _c_file_info = Gio.SimpleAction.new("file_info", None)
        _c_file_info.connect("activate", self._card.show_info)
        _actions.add_action(_c_sync)
        _actions.add_action(_c_rew100)
        _actions.add_action(_c_forw100)
        _actions.add_action(_c_rplay)
        _actions.add_action(_c_file_info)
        self.insert_action_group("controls", _actions)
        shortcut_controller = Gtk.ShortcutController()
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>Return"),
                action=Gtk.NamedAction.new("controls.sync"),
            )
        )
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>minus"),
                action=Gtk.NamedAction.new("controls.rew100"),
            )
        )
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>equal"),
                action=Gtk.NamedAction.new("controls.forw100"),
            )
        )
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>z"),
                action=Gtk.NamedAction.new("controls.rplay"),
            )
        )
        self.add_controller(shortcut_controller)

        # Lines actions
        _actions = Gio.SimpleActionGroup.new()
        _l_append = Gio.SimpleAction.new("append", None)
        _l_append.connect("activate", self.append_line)
        _l_remove = Gio.SimpleAction.new("remove", None)
        _l_remove.connect("activate", self._remove_line)
        _l_prepend = Gio.SimpleAction.new("prepend", None)
        _l_prepend.connect("activate", self._prepend_line)
        _l_append_end = Gio.SimpleAction.new("append_end", None)
        _l_append_end.connect("activate", self._append_end_line)
        _actions.add_action(_l_append)
        _actions.add_action(_l_remove)
        _actions.add_action(_l_prepend)
        _actions.add_action(_l_append_end)
        self.insert_action_group("line", _actions)
        shortcut_controller = Gtk.ShortcutController()
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt><primary>a"),
                action=Gtk.NamedAction.new("line.append_end"),
            )
        )
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>r"),
                action=Gtk.NamedAction.new("line.remove"),
            )
        )
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>a"),
                action=Gtk.NamedAction.new("line.append"),
            )
        )
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Alt>p"),
                action=Gtk.NamedAction.new("line.prepend"),
            )
        )
        self.add_controller(shortcut_controller)


class LRCSyncLine(Adw.EntryRow):
    __gtype_name__ = "LRCSyncLine"

    def __init__(self, text: str = "") -> "LRCSyncLine":
        super().__init__(editable=True, text=text)
        self.add_css_class("property")
        self.focus_controller = Gtk.EventControllerFocus()
        self.focus_controller.connect("enter", self._on_selected)
        self.add_controller(self.focus_controller)
        self.connect("entry-activated", self.add_line_on_enter)

        for item in self.get_child():
            for _item in item:
                if isinstance(_item, Gtk.Text):
                    self.text_field = _item
                    break
        self.text_field.connect("backspace", self.remove_line_on_backspace)

    def _on_selected(self, *_args) -> None:
        self.get_ancestor(LRCSyncPage).selected_line = self

    def add_line_on_enter(self, *_args) -> None:
        """Add a new line when Enter is pressed"""
        self.get_ancestor(LRCSyncPage).append_line()

    def remove_line_on_backspace(self, text: Gtk.Text) -> None:
        if text.get_text_length() == 0:
            page: LRCSyncPage = self.get_ancestor(LRCSyncPage)
            lines = []
            for line in page.sync_lines:
                lines.append(line)
            index = lines.index(self)
            page.sync_lines.remove(self)
            if (row := page.sync_lines.get_row_at_index(index - 1)) is not None:
                row.grab_focus()
