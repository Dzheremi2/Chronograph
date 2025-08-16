"""Word-by-Word syncing page"""

from typing import Union

from dgutils.actions import Actions
from gi.repository import Adw, Gio, GLib, GObject, Gtk

from chronograph.internal import Constants, Schema
from chronograph.ui.widgets.player import Player
from chronograph.ui.widgets.song_card import SongCard
from chronograph.ui.widgets.wbw.lyrics_widget import LyricsWidget
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable
from chronograph.utils.wbw.models.lyrics_model import LyricsModel

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/sync_pages/WBWSyncPage.ui")
# @Actions.from_schema(Constants.PREFIX + "/resources/actions/wbw_sync_page_actions.yaml")
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
    review_view_stack_page: Adw.ViewStackPage = gtc()
    review_layout_container: Adw.Bin = gtc()

    selected_format: str = Schema.get_default_format()

    def __init__(
        self, card: SongCard, file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable]
    ) -> None:
        super().__init__()
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

        # TODO: Implement param support to DGutils Actions module
        group = Gio.SimpleActionGroup.new()
        act = Gio.SimpleAction.new("format", GLib.VariantType.new("s"))
        act.connect("activate", self._on_format_changed)
        group.add_action(act)
        self.insert_action_group("root", group)

        if self.selected_format == "elrc":
            self.format_menu_button.set_label("eLRC")
        elif self.selected_format == "ttml":
            self.format_menu_button.set_label("TTML")

        with open("/home/dzheremi/Repos/Chronograph/elrc.lrc") as f:
            self.lyrics_layout_container.set_child(LyricsModel(f.read()).widget)

    def _on_format_changed(self, _action, param: GLib.Variant) -> None:
        if param.get_string() == "elrc":
            self.selected_format = "elrc"
            self.format_menu_button.set_label("eLRC")
        elif param.get_string() == "ttml":
            self.selected_format = "ttml"
            self.format_menu_button.set_label("TTML")
