"""Sync page for LRC format syncing"""

import hashlib
import re
import threading
from binascii import unhexlify
from pathlib import Path
from typing import Literal, Optional, Union

import requests
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from chronograph.internal import Constants, Schema
from chronograph.ui.widgets.player import Player
from chronograph.ui.widgets.song_card import SongCard
from chronograph.utils.converter import mcs_to_timestamp, timestamp_to_mcs
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable

gtc = Gtk.Template.Child  # pylint: disable=invalid-name

PANGO_HIGHLIGHTER = Pango.AttrList().from_string("0 -1 weight ultrabold")


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/sync_pages/LRCSyncPage.ui")
class LRCSyncPage(Adw.NavigationPage):
    __gtype_name__ = "LRCSyncPage"

    header_bar: Adw.HeaderBar = gtc()
    player_container: Gtk.Box = gtc()
    export_lyrics_button: Gtk.MenuButton = gtc()
    sync_page_metadata_editor_button: Gtk.Button = gtc()
    sync_lines_scrolled_window: Gtk.ScrolledWindow = gtc()
    sync_lines: Gtk.ListBox = gtc()
    selected_line: Optional["LRCSyncLine"] = None

    _autosave_timeout_id: Optional[int] = None

    def __init__(
        self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
    ) -> "LRCSyncPage":
        super().__init__()
        self._card: SongCard = card
        self._file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable] = file
        self._card.bind_property(
            "title", self, "title", GObject.BindingFlags.SYNC_CREATE
        )
        self.sync_page_metadata_editor_button.connect(
            "clicked", self._card.open_metadata_editor
        )
        self._player_widget = Player(file, card)
        self._player = self._player_widget._player
        self._player.connect("notify::timestamp", self._on_timestamp_changed)
        self.player_container.append(self._player_widget)

        self._autosave_path = Path(self._file.path).with_suffix(Schema.auto_file_format)

        self.connect("hidden", self._on_page_closed)
        self._close_rq_handler_id = Constants.WIN.connect(
            "close-request", self._on_app_close
        )

        # Automatically load the lyrics file if it exists
        if Schema.auto_file_manipulation and self._autosave_path.exists():
            metatags_filterout = re.compile(r"^\[\w+:[^\]]+\]$")
            timed_line_pattern = re.compile(r"^(\[\d{2}:\d{2}\.\d{2,3}\])(\S)")
            with open(self._autosave_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()

            filtered_lines = [
                line for line in lines if not metatags_filterout.match(line)
            ]
            normalized_lines = [
                timed_line_pattern.sub(r"\1 \2", line) for line in filtered_lines
            ]

            self.sync_lines.remove_all()
            for line in normalized_lines:
                self.sync_lines.append(LRCSyncLine(line))

        self._setup_actions()

    ############### Line Actions ###############
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

    ###############

    ############### Sync Actions ###############
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

        clipboard = Gdk.Display().get_default().get_clipboard()
        clipboard.read_text_async(None, __on_clipboard_parsed, user_data=clipboard)

    def _import_file(self, *_args) -> None:
        metatags_filterout = re.compile(r"^\[\w+:[^\]]+\]$")
        timed_line_pattern = re.compile(r"^(\[\d{2}:\d{2}\.\d{2,3}\])(\S)")

        def __on_selected_lyrics_file(
            file_dialog: Gtk.FileDialog, result: Gio.Task
        ) -> None:
            path = file_dialog.open_finish(result).get_path()
            with open(path, "r", encoding="utf-8") as file:
                lines = file.read().splitlines()

            filtered_lines = [
                line for line in lines if not metatags_filterout.match(line)
            ]
            normalized_lines = [
                timed_line_pattern.sub(r"\1 \2", line) for line in filtered_lines
            ]

            self.sync_lines.remove_all()
            for _, line in enumerate(normalized_lines):
                self.sync_lines.append(LRCSyncLine(line))

        dialog = Gtk.FileDialog(
            default_filter=Gtk.FileFilter(mime_types=["text/plain"])
        )
        dialog.open(Constants.WIN, None, __on_selected_lyrics_file)

    # pylint: disable=import-outside-toplevel
    def _import_lrclib(self, *_args) -> None:
        from chronograph.ui.dialogs.lrclib import LRClib

        lrclib_dialog = LRClib()
        lrclib_dialog.present(Constants.WIN)

    ###############

    ############### Export Actions ###############

    def _export_clipboard(self, *_args) -> None:
        string = ""
        for line in self.sync_lines:  # pylint: disable=not-an-iterable
            string += line.get_text() + "\n"
        string = string.strip()
        clipboard = Gdk.Display().get_default().get_clipboard()
        clipboard.set(string)
        Constants.WIN.show_toast(_("Lyrics exported to clipboard"), timeout=3)

    def _export_file(self, *_args) -> None:

        def __on_export_file_selected(
            file_dialog: Gtk.FileDialog, result: Gio.Task, lyrics: str
        ) -> None:
            filepath = file_dialog.save_finish(result).get_path()
            with open(filepath, "w") as f:
                f.write(lyrics)

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
            initial_name=Path(self._file.path).stem + Schema.auto_file_format
        )
        dialog.save(Constants.WIN, None, __on_export_file_selected, lyrics)

    ###############

    def _on_timestamp_changed(self, media_stream: Gtk.MediaStream, *_args) -> None:
        try:
            lines: list[LRCSyncLine] = []
            timestamps: list[int] = []
            for line in self.sync_lines:  # pylint: disable=not-an-iterable
                line.set_attributes(None)
                try:
                    timing = timestamp_to_mcs(line.get_text())
                    lines.append(line)
                    timestamps.append(timing)
                except ValueError:
                    break

            if not timestamps:
                return

            timestamp = media_stream.get_timestamp()
            if timestamp < timestamps[0]:
                lines[0].set_attributes(PANGO_HIGHLIGHTER)
                return
            for i in range(len(timestamps) - 1):
                if timestamps[i] <= timestamp < timestamps[i + 1]:
                    lines[i].set_attributes(PANGO_HIGHLIGHTER)
                    return
            if timestamp >= timestamps[-1]:
                lines[-1].set_attributes(PANGO_HIGHLIGHTER)
        except IndexError:
            pass

    ############### Autosave Actions ###############

    def reset_timer(self) -> None:
        if self._autosave_timeout_id:
            GLib.source_remove(self._autosave_timeout_id)
        if Schema.auto_file_manipulation:
            self._autosave_timeout_id = GLib.timeout_add(
                Schema.autosave_throttling * 1000, self._autosave
            )

    def _autosave(self) -> Literal[False]:
        if Schema.auto_file_manipulation:
            try:
                with open(self._autosave_path, "w", encoding="utf-8") as f:
                    for line in self.sync_lines:  # pylint: disable=not-an-iterable
                        f.write(line.get_text() + "\n")
            except Exception as e:
                print(f"Autosave failed: {e}")  # TODO: Log this
            self._autosave_timeout_id = None
        return False

    def _on_page_closed(self, *_args):
        Constants.WIN.disconnect(self._close_rq_handler_id)
        if self._autosave_timeout_id:
            GLib.source_remove(self._autosave_timeout_id)
        if Schema.auto_file_manipulation:
            self._autosave()

    def _on_app_close(self, *_):
        if self._autosave_timeout_id:
            GLib.source_remove(self._autosave_timeout_id)
        if Schema.auto_file_manipulation:
            self._autosave()
        return False

    ###############

    ############### Publisher ###############

    def _publish(
        self, __, ___, title: str, artist: str, album: str, duration: str, lyrics: str
    ) -> None:

        def _verify_nonce(result: int, target: int) -> bool:
            if len(result) != len(target):
                return False

            for index, res in enumerate(result):
                if res > target[index]:
                    return False
                if res < target[index]:
                    break

            return True

        def _solve_challenge(prefix: str, target_hex: str) -> str:
            target = unhexlify(target_hex.upper())
            nonce = 0

            while True:
                input_data = f"{prefix}{nonce}".encode()
                hashed = hashlib.sha256(input_data).digest()

                if _verify_nonce(hashed, target):
                    break
                nonce += 1

            return str(nonce)

        def _make_plain_lyrics(lyrics: str) -> str:
            pattern = r"\[.*?\] "
            lyrics = lyrics.splitlines()
            plain_lyrics = []
            for line in lyrics:
                plain_lyrics.append(re.sub(pattern, "", line))
            return "\n".join(plain_lyrics[:-1])

        def _do_publish(
            title: str, artist: str, album: str, duration: str, lyrics: str
        ) -> None:
            _err = None
            try:
                challenge_data = requests.post(
                    url="https://lrclib.net/api/request-challenge", timeout=10
                )
            except requests.exceptions.ConnectionError as e:
                Constants.WIN.show_toast(_("Failed to connect to LRClib.net"))
                _err = e
            except requests.exceptions.Timeout as e:
                Constants.WIN.show_toast(_("Connection to LRClib.net timed out"))
                _err = e
            except Exception as e:
                Constants.WIN.show_toast(
                    _("An error occurred while connecting to LRClib.net")
                )
                _err = e
            finally:
                if _err:
                    print(_err)  # TODO: Log this
                    self.export_lyrics_button.set_sensitive(True)
                    self.export_lyrics_button.set_icon_name("export-to-symbolic")
                    return  # pylint: disable=return-in-finally, lost-exception

            challenge_data = challenge_data.json()
            nonce = _solve_challenge(
                prefix=challenge_data["prefix"], target_hex=challenge_data["target"]
            )
            # TODO: Log X-Publish-Token

            _err = None
            try:
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
                        "plainLyrics": _make_plain_lyrics(lyrics),
                        "syncedLyrics": lyrics,
                    },
                    timeout=10,
                )
            except requests.exceptions.ConnectionError as e:
                Constants.WIN.show_toast(_("Failed to connect to LRClib.net"))
                _err = e
            except requests.exceptions.Timeout as e:
                Constants.WIN.show_toast(_("Connection to LRClib.net timed out"))
                _err = e
            except Exception as e:
                Constants.WIN.show_toast(
                    _("An error occurred while connecting to LRClib.net")
                )
                _err = e
            finally:
                self.export_lyrics_button.set_sensitive(True)
                self.export_lyrics_button.set_icon_name("export-to-symbolic")
                if _err:
                    print(_err)  # TODO: Log this
                    return  # pylint: disable=return-in-finally, lost-exception

            # TODO: Log all this
            if response.status_code == 201:
                Constants.WIN.show_toast(
                    _("Published successfully: {}").format(str(response.status_code)),
                )
            elif response.status_code == 400:
                Constants.WIN.show_toast(
                    _("Incorrect publish token: {}").format(str(response.status_code)),
                )
            else:
                Constants.WIN.show_toast(
                    _("Unknown error occured: {}").format(str(response.status_code)),
                )

        if not all((title, artist, album, duration, lyrics)):

            def _reason() -> None:
                Adw.AlertDialog(
                    heading=_("Unable to publish lyrics"),
                    body=_(
                        "To publish lyrics the track must have a title, artist, album and lyrics fields set"
                    ),
                ).present(Constants.WIN)

            Constants.WIN.show_toast(
                _("Cannot publish empty lyrics"),
                button_label=_("Why?"),
                button_callback=_reason,
            )
            return
        self.export_lyrics_button.set_sensitive(False)
        self.export_lyrics_button.set_child(Adw.Spinner())
        threading.Thread(
            target=_do_publish,
            args=(title, artist, album, duration, lyrics),
            daemon=True,
        ).start()

    ###############

    # pylint: disable=too-many-locals, too-many-statements, not-an-iterable
    def _setup_actions(self) -> None:
        # Import actions
        _actions = Gio.SimpleActionGroup.new()
        _i_lrclib = Gio.SimpleAction.new("lrclib", None)
        _i_lrclib.connect("activate", self._import_lrclib)
        _i_file = Gio.SimpleAction.new("file", None)
        _i_file.connect("activate", self._import_file)
        _i_clipboard = Gio.SimpleAction.new("clipboard", None)
        _i_clipboard.connect("activate", self._import_clipboard)
        _actions.add_action(_i_lrclib)
        _actions.add_action(_i_file)
        _actions.add_action(_i_clipboard)
        self.insert_action_group("import", _actions)

        # Export actions
        _actions = Gio.SimpleActionGroup.new()
        _e_lrclib = Gio.SimpleAction.new("lrclib", None)
        _e_lrclib.connect(
            "activate",
            self._publish,
            self._card.title,
            self._card.artist,
            self._card.album,
            self._card.duration,
            "\n".join(line.get_text() for line in self.sync_lines).rstrip("\n"),
        )
        _e_file = Gio.SimpleAction.new("file", None)
        _e_file.connect("activate", self._export_file)
        _e_clipboard = Gio.SimpleAction.new("clipboard", None)
        _e_clipboard.connect("activate", self._export_clipboard)
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
        self.connect("changed", self._reset_timer)

        for item in self.get_child():
            for _item in item:
                if isinstance(_item, Gtk.Text):
                    self.text_field = _item
                    break
        self.text_field.connect("backspace", self._remove_line_on_backspace)

    def _on_selected(self, *_args) -> None:
        self.get_ancestor(LRCSyncPage).selected_line = self

    def add_line_on_enter(self, *_args) -> None:
        """Add a new line when Enter is pressed"""
        self.get_ancestor(LRCSyncPage).append_line()

    def _reset_timer(self, *_args) -> None:
        self.get_ancestor(LRCSyncPage).reset_timer()

    def _remove_line_on_backspace(self, text: Gtk.Text) -> None:
        if text.get_text_length() == 0:
            page: LRCSyncPage = self.get_ancestor(LRCSyncPage)
            lines = []
            for line in page.sync_lines:
                lines.append(line)
            index = lines.index(self)
            page.sync_lines.remove(self)
            if (row := page.sync_lines.get_row_at_index(index - 1)) is not None:
                row.grab_focus()
