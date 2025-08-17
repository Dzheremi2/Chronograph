"""Word-by-Word syncing page"""

import re
from pathlib import Path
from typing import Optional, Union

from dgutils.actions import Actions
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from chronograph.internal import Constants, Schema
from chronograph.ui.widgets.player import Player
from chronograph.ui.widgets.song_card import SongCard
from chronograph.utils.converter import mcs_to_timestamp, timestamp_to_mcs
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable
from chronograph.utils.wbw.elrc_parser import eLRCParser
from chronograph.utils.wbw.models.lyrics_model import LyricsModel

gtc = Gtk.Template.Child  # pylint: disable=invalid-name
logger = Constants.LOGGER


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/sync_pages/WBWSyncPage.ui")
@Actions.from_schema(Constants.PREFIX + "/resources/actions/wbw_sync_page_actions.yaml")
class WBWSyncPage(Adw.NavigationPage):
    __gtype_name__ = "WBWSyncPage"

    format_menu_button: Gtk.MenuButton = gtc()
    player_container: Gtk.Box = gtc()
    sync_page_metadata_editor_button: Gtk.Button = gtc()
    modes: Adw.ViewStack = gtc()
    edit_view_stack_page: Adw.ViewStackPage = gtc()
    edit_view_text_view: Gtk.TextView = gtc()
    sync_view_stack_page: Adw.ViewStackPage = gtc()
    lyrics_layout_container: Adw.Bin = gtc()

    _selected_format: str = Schema.get_default_format()
    _lyrics_model: LyricsModel

    def __init__(
        self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
    ) -> None:
        super().__init__()

        # Workaround, since Adw.InlineViewSwitcher doen't have singnal for describing
        # previous and newly selected page
        self._current_page: Adw.ViewStackPage = self.edit_view_stack_page
        self._previous_page: Optional[Adw.ViewStackPage] = None

        # Player setup
        self._card: SongCard = card
        self._file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable] = file
        self._card.bind_property(
            "title", self, "title", GObject.BindingFlags.SYNC_CREATE
        )
        self.sync_page_metadata_editor_button.connect(
            "clicked", self._card.open_metadata_editor
        )
        if isinstance(self._card._file, FileUntaggable):
            self.sync_page_metadata_editor_button.set_visible(False)
        self._player_widget = Player(file, card)
        self._player = self._player_widget._player
        self.player_container.append(self._player_widget)

        self._autosave_path = Path(self._file.path).with_suffix(
            Schema.get_auto_file_format()
        )

        # TODO: Implement param support to DGutils Actions module
        group = Gio.SimpleActionGroup.new()
        act = Gio.SimpleAction.new("format", GLib.VariantType.new("s"))
        act.connect("activate", self._on_format_changed)
        group.add_action(act)
        self.insert_action_group("root", group)

        self.modes.connect("notify::visible-child", self._page_visibility)

        # Set initial label for format selector button
        if self._selected_format == "wbw":
            self.format_menu_button.set_label("eLRC")
        elif self._selected_format == "ttml":
            self.format_menu_button.set_label("TTML")

        # Automatically load the lyrics file if it exists
        if Schema.get_auto_file_manipulation() and self._autosave_path.exists():
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

            buffer = Gtk.TextBuffer()
            buffer.set_text("\n".join(normalized_lines))
            self.edit_view_text_view.set_buffer(buffer)

    def _page_visibility(self, stack: Adw.ViewStack, _pspec) -> None:
        page: Adw.ViewStackPage = stack.get_page(stack.get_visible_child())
        self._previous_page = self._current_page
        self._current_page = page
        self._on_page_switched(self._previous_page, self._current_page)

    def _on_page_switched(
        self, prev_page: Adw.ViewStackPage, new_page: Adw.ViewStackPage
    ) -> None:
        if (
            prev_page == self.edit_view_stack_page
            and new_page == self.sync_view_stack_page
        ):
            lyrics = self.edit_view_text_view.get_buffer().get_text(
                self.edit_view_text_view.get_buffer().get_start_iter(),
                self.edit_view_text_view.get_buffer().get_end_iter(),
                False,
            )
            if lyrics != "":
                self.lyrics_layout_container.set_child(
                    (model := LyricsModel(lyrics)).widget
                )
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
                        description=_(
                            "You've not provided any lyrics for synchronization"
                        ),
                        icon_name="nothing-found-symbolic",
                    )
                )

        if (
            prev_page == self.sync_view_stack_page
            and new_page == self.edit_view_stack_page
        ):
            lyrics = eLRCParser.create_lyrics_elrc(self._lyrics_model.get_tokens())
            buffer = Gtk.TextBuffer()
            buffer.set_text(lyrics)
            self.edit_view_text_view.set_buffer(buffer)

    def _on_format_changed(self, _action, param: GLib.Variant) -> None:
        if param.get_string() == "elrc":
            self._selected_format = "wbw"
            self.format_menu_button.set_label("eLRC")
        elif param.get_string() == "ttml":
            self._selected_format = "ttml"
            self.format_menu_button.set_label("TTML")

    ############### Import Actions ###############
    def _import_lrclib(self, *_args) -> None:
        from chronograph.ui.dialogs.lrclib import LRClib

        lrclib_dialog = LRClib()
        lrclib_dialog.present(Constants.WIN)
        logger.debug("LRClib import dialog shown")

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

            buffer = Gtk.TextBuffer()
            buffer.set_text("\n".join(normalized_lines).rstrip())
            self.edit_view_text_view.set_buffer(buffer)
            logger.info("Imported lyrics from file")

        dialog = Gtk.FileDialog(
            default_filter=Gtk.FileFilter(mime_types=["text/plain"])
        )
        dialog.open(Constants.WIN, None, __on_selected_lyrics_file)

    def _import_clipboard(self, *_args) -> None:

        def __on_clipboard_parsed(
            _clipboard, result: Gio.Task, clipboard: Gdk.Clipboard
        ) -> None:
            data = clipboard.read_text_finish(result)
            buffer = Gtk.TextBuffer()
            buffer.set_text(data)
            self.edit_view_text_view.set_buffer(buffer)
            logger.info("Imported lyrics from clipboard")

        clipboard = Gdk.Display().get_default().get_clipboard()
        clipboard.read_text_async(None, __on_clipboard_parsed, user_data=clipboard)

    ###############

    ############### Export Actions ###############
    def _export_file(self, *_args) -> None:

        def __on_export_file_selected(
            file_dialog: Gtk.FileDialog, result: Gio.Task, lyrics: str
        ) -> None:
            filepath = file_dialog.save_finish(result).get_path()
            with open(filepath, "w") as f:
                f.write(lyrics)
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
                False,
            )
        else:
            if not isinstance(self.lyrics_layout_container.get_child(), Adw.StatusPage):
                lyrics = eLRCParser.create_lyrics_elrc(self._lyrics_model.get_tokens())
            else:
                lyrics = ""

        dialog = Gtk.FileDialog(
            initial_name=Path(self._file.path).stem + Schema.get_auto_file_format()
        )
        dialog.save(Constants.WIN, None, __on_export_file_selected, lyrics)

    def _export_clipboard(self, *_args) -> None:
        if self._current_page == self.edit_view_stack_page:
            lyrics = self.edit_view_text_view.get_buffer().get_text(
                self.edit_view_text_view.get_buffer().get_start_iter(),
                self.edit_view_text_view.get_buffer().get_end_iter(),
                False,
            )
        else:
            if not isinstance(self.lyrics_layout_container.get_child(), Adw.StatusPage):
                lyrics = eLRCParser.create_lyrics_elrc(self._lyrics_model.get_tokens())
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
        mcs = self._player.get_timestamp()
        ms = mcs // 1000
        current_word.set_property("time", ms)
        logger.debug(
            "Word “%s” was synced with timestamp %s",
            current_word.word,
            mcs_to_timestamp(mcs),
        )
        current_line.next()

    def _replay(self, *_args) -> None:
        current_line = self._lyrics_model.get_current_line()
        current_word = current_line.get_current_word()
        mcs = timestamp_to_mcs(
            f"[{current_word.timestamp}]"
        )  # I'm lazy to refactor this method, so `[]` were added :)
        self._player.seek(mcs)
        logger.debug("Replayed word at timing: %s", mcs_to_timestamp(mcs))

    def _seek100(self, _action, _param, mcs_seek: int) -> None:
        current_line = self._lyrics_model.get_current_line()
        current_word = current_line.get_current_word()
        ms = current_word.time
        mcs = ms * 1000
        mcs_new = mcs + mcs_seek
        mcs_new = max(mcs_new, 0)
        current_word.set_property("time", mcs_new // 1000)
        self._player.seek(mcs_new)
        logger.debug(
            "Word(%s) was seeked %sms to %s",
            current_word,
            mcs_seek // 1000,
            mcs_to_timestamp(mcs_new),
        )

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
