from gettext import pgettext as C_
from typing import Union

from gi.repository import Gdk, GObject, Gtk

from chronograph.internal import Constants
from chronograph.ui.BoxDialog import BoxDialog
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


class SongCardInternals(GObject.Object):
    __gtype_name__ = "SongCardInternals"

    def __init__(
        self, file: Union[FileID3, FileVorbis, FileMP4, FileUntaggable]
    ) -> "SongCardInternals":
        super().__init__()
        self._file = file
        self.set_property("title", self._file.title)
        self.set_property("artist", self._file.artist)
        self.set_property("album", self._file.album)

    @GObject.Property(type=str, default=C_("song title placeholder", "Unknown"))
    def title(self) -> str:
        """Title of the song"""
        return self._file.title or C_("song title placeholder", "Unknown")

    @title.setter
    def title(self, value: str) -> None:
        self._file.title = value

    @GObject.Property(type=str, default=C_("song artist placeholder", "Unknown"))
    def artist(self) -> str:
        """Artist of the song"""
        return self._file.artist or C_("song artist placeholder", "Unknown")

    @artist.setter
    def artist(self, value: str) -> None:
        self._file.artist = value

    @GObject.Property(type=str, default=C_("song album placeholder", "Unknown"))
    def album(self) -> str:
        """Album of the song"""
        return self._file.album or C_("song album placeholder", "Unknown")

    @album.setter
    def album(self, value: str) -> None:
        self._file.album = value

    @GObject.Property()
    def cover(self) -> Gdk.Texture:
        """Cover of the song"""
        return self._file.get_cover_texture()

    @cover.setter
    def cover(self, path: str) -> None:
        self._file.set_cover(path)

    @GObject.Property(type=str)
    def path(self) -> str:
        """Path to the loaded song"""
        return self._file.path


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/SongCard.ui")
class SongCard(Gtk.Box):
    __gtype_name__ = "SongCard"

    buttons_revealer: Gtk.Revealer = gtc()
    play_button: Gtk.Button = gtc()
    metadata_editor_button: Gtk.Button = gtc()
    info_button: Gtk.Button = gtc()
    cover_button: Gtk.Button = gtc()
    cover_img: Gtk.Image = gtc()
    title_label: Gtk.Label = gtc()
    artist_label: Gtk.Label = gtc()

    def __init__(
        self, file: Union[FileID3, FileVorbis, FileMP4, FileUntaggable], **kwargs
    ) -> "SongCard":
        self._data: SongCardInternals = SongCardInternals(file)
        super().__init__(**kwargs)
        self._data.bind_property(
            "title", self.title_label, "label", GObject.BindingFlags.SYNC_CREATE
        )
        self._data.bind_property(
            "artist", self.artist_label, "label", GObject.BindingFlags.SYNC_CREATE
        )
        self.cover_img.set_from_paintable(self._data.cover)
        self._data.bind_property(
            "cover", self.cover_img, "paintable", GObject.BindingFlags.DEFAULT
        )

        event_controller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(event_controller_motion)
        event_controller_motion.connect("enter", self._toggle_buttons)
        event_controller_motion.connect("leave", self._toggle_buttons)

        if isinstance(file, FileUntaggable):
            self.metadata_editor_button.set_visible(False)

    def _toggle_buttons(self, *_args) -> None:
        self.buttons_revealer.set_reveal_child(
            not self.buttons_revealer.get_reveal_child()
        )

    @Gtk.Template.Callback()
    def show_info(self, *_args) -> None:
        """Show song info dialog"""
        BoxDialog(
            C_("song info dialog", "About File"),
            (
                (_("Title"), self._data.title),
                (_("Artist"), self._data.artist),
                (_("Album"), self._data.album),
                (_("Path"), self._data.path),
            ),
        ).present(Constants.WIN)
