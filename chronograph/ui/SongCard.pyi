from typing import Union

from gi.repository import Gtk

from chronograph.utils.file_mutagen_id3 import FileID3
from chronograph.utils.file_mutagen_vorbis import FileVorbis  # type: ignore

class SongCard(Gtk.Box):
    """Card with Title, Artist and Cover of provided file

    Parameters
    ----------
    file : Union[FileID3, FileVorbis]
        File of `.ogg`, `.flac`, `.mp3` and `.wav` formats

    GTK Objects
    ----------
    ::

        buttons_revealer: Gtk.Revealer -> Revealer for Play and Edit buttons
        play_button: Gtk.Button -> Play button
        metadata_editor_button: Gtk.Button -> Metadata editor button
        cover_button: Gtk.Button -> Clickable cover of song
        cover: Gtk.Image -> Cover image of song
        title_label: Gtk.Label -> Title of song
        artist_label: Gtk.Label -> Artist of song
    """

    buttons_revealer: Gtk.Revealer
    play_button: Gtk.Button
    metadata_editor_button: Gtk.Button
    info_button: Gtk.Button
    cover_button: Gtk.Button
    cover_img: Gtk.Image
    title_label: Gtk.Label
    artist_label: Gtk.Label

    _file: Union[FileID3, FileVorbis]

    def toggle_buttons(self, *_args) -> None: ...
    def invalidate_update(self, property: str) -> None: ...
    def invalidate_cover(self) -> None: ...
    def bind_props(self) -> None: ...
