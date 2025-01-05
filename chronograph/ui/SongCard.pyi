from typing import Union

from gi.repository import Gtk, Adw

from chronograph.utils.file_mutagen_id3 import FileID3
from chronograph.utils.file_mutagen_vorbis import FileVorbis  # type: ignore

label_str: str
title_str: str
artist_str: str
album_str: str
path_str: str

class SongCard(Gtk.Box):
    """Card with Title, Artist and Cover of provided file

    Parameters
    ----------
    file : Union[FileID3, FileVorbis]
        File of `.ogg`, `.flac`, `.mp3` and `.wav` formats
    """

    buttons_revealer: Gtk.Revealer
    play_button: Gtk.Button
    metadata_editor_button: Gtk.Button
    info_button: Gtk.Button
    cover_button: Gtk.Button
    cover_img: Gtk.Image
    title_label: Gtk.Label
    artist_label: Gtk.Label

    # Metadata editor
    metadata_editor: Adw.Dialog
    metadata_editor_title_row: Adw.EntryRow
    metadata_editor_artist_row: Adw.EntryRow
    metadata_editor_album_row: Adw.EntryRow
    metadata_editor_apply_button: Gtk.Button
    metadata_editor_cancel_button: Gtk.Button

    _file: Union[FileID3, FileVorbis]

    def toggle_buttons(self, *_args) -> None: ...
    def invalidate_update(self, property: str, scope: str = "self") -> None: ...
    def invalidate_cover(self, widget: Gtk.Image) -> None: ...
    def bind_props(self) -> None: ...
    def on_play_button_clicked(self, *_args) -> None: ...
    def open_metadata_editor(self, *_args) -> None: ...
    def metadata_editor_save(self, *_args) -> None: ...
    def on_metadata_editor_close(self, *_args) -> None: ...

