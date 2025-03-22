from typing import Union

from gi.repository import Adw, Gio, Gtk

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

    # Card widget
    buttons_revealer: Gtk.Revealer
    play_button: Gtk.Button
    metadata_editor_button: Gtk.Button
    info_button: Gtk.Button
    cover_button: Gtk.Button
    cover_img: Gtk.Image
    title_label: Gtk.Label
    artist_label: Gtk.Label

    # ActionRow widget
    list_view_row: Adw.ActionRow
    cover_img_row: Gtk.Image
    buttons_revealer_row: Gtk.Revealer
    play_button_row: Gtk.Button
    metadata_editor_button_row: Gtk.Button
    info_button_row: Gtk.Button

    # Metadata editor Dialog
    metadata_editor: Adw.Dialog
    metadata_editor_cancel_button: Gtk.Button
    metadata_editor_apply_button: Gtk.Button
    metadata_editor_cover_image: Gtk.Image
    metadata_editor_cover_button: Gtk.MenuButton
    metadata_editor_props: Gtk.ListBox
    metadata_editor_title_row: Adw.EntryRow
    metadata_editor_artist_row: Adw.EntryRow
    metadata_editor_album_row: Adw.EntryRow

    _file: Union[FileID3, FileVorbis]
    _mde_new_cover_path: str

    def on_play_button_clicked(self, *_args) -> None: ...
    def open_metadata_editor(self, *_args) -> None: ...
    def metadata_editor_save(self, *_args) -> None: ...
    def metadata_change_cover(self, *_args) -> None: ...
    def on_metadata_change_cover(
        self, dialog: Gtk.FileDialog, result: Gio.Task
    ) -> None: ...
    def metadata_remove_cover(self, *_args) -> None: ...
    def on_metadata_editor_close(self, *_args) -> None: ...
    def on_metadata_editor_closed(self, *_args) -> None: ...
    def gen_box_dialog(self, *_args) -> None: ...
    def toggle_buttons(self, *_args) -> None: ...
    def toggle_buttons_row(self, *_args) -> None: ...
    def invalidate_cover(self, widget: Gtk.Image) -> None: ...
    def get_list_mode(self) -> Adw.ActionRow: ...
