from typing import Union

from gi.repository import Adw, GObject, Gtk

from chronograph.internal import Constants
from chronograph.ui.song_card import SongCard
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/PlayerUI.ui")
class PlayerUI(Adw.BreakpointBin):
    __gtype_name__ = "PlayerUI"

    main_clamp: Adw.Clamp = gtc()
    sync_page_cover: Gtk.Image = gtc()
    title_inscr: Gtk.Inscription = gtc()
    artist_inscr: Gtk.Inscription = gtc()
    non_collapse_box: Gtk.Box = gtc()
    player_box: Gtk.Box = gtc()
    media_controls: Gtk.MediaControls = gtc()
    repeat_button: Gtk.ToggleButton = gtc()
    collapse_box: Gtk.Box = gtc()

    def __init__(
        self,
        file: Union[FileID3, FileMP4, FileVorbis, FileUntaggable],
        card: SongCard,
        max_width: int = 600,
    ) -> "PlayerUI":
        super().__init__()
        self._player = Gtk.MediaFile.new_for_filename(card.path)
        # self._player.connect("notify::timestamp", self._on_timestamp_updated)
        self.media_controls.set_media_stream(self._player)
        self._file = file
        self._card = card
        self.main_clamp.set_maximum_size(max_width)
        self.main_clamp.set_tightening_threshold(max_width)

        self._card.bind_property(
            "title", self.title_inscr, "text", GObject.BindingFlags.SYNC_CREATE
        )
        self._card.bind_property(
            "artist", self.artist_inscr, "text", GObject.BindingFlags.SYNC_CREATE
        )
        self._card.bind_property(
            "cover",
            self.sync_page_cover,
            "paintable",
            GObject.BindingFlags.SYNC_CREATE,
        )

    @Gtk.Template.Callback()
    def on_breakpoint(self, *_args) -> None:
        """Changes the player slider position based on the breakpoint state"""
        if self.collapse_box.get_first_child() is None:
            self.non_collapse_box.remove(self.player_box)
            self.collapse_box.append(self.player_box)
        else:
            self.collapse_box.remove(self.player_box)
            self.non_collapse_box.append(self.player_box)

    @Gtk.Template.Callback()
    def on_repeat_button_toggled(self, button: Gtk.ToggleButton) -> None:
        self._player.set_loop(button.get_active())
