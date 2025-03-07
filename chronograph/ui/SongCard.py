import os
import pathlib
from typing import Union

from gi.repository import Adw, Gdk, Gio, GObject, Gtk  # type: ignore

from chronograph import shared
from chronograph.ui.BoxDialog import BoxDialog
from chronograph.utils.file_mutagen_id3 import FileID3
from chronograph.utils.file_mutagen_vorbis import FileVorbis
from chronograph.utils.parsers import file_parser

label_str: str = _("About File")
title_str: str = _("Title")
artist_str: str = _("Artist")
album_str: str = _("Album")
path_str: str = _("Path")


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/SongCard.ui")
class SongCard(Gtk.Box):
    """Card with Title, Artist and Cover of provided file

    Parameters
    ----------
    file : FileID3 | FileVorbis
        File of `.ogg`, `.flac`, `.mp3` and `.wav` formats
    """

    __gtype_name__ = "SongCard"

    # Card widget
    buttons_revealer: Gtk.Revealer = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    metadata_editor_button: Gtk.Button = Gtk.Template.Child()
    info_button: Gtk.Button = Gtk.Template.Child()
    cover_button: Gtk.Button = Gtk.Template.Child()
    cover_img: Gtk.Image = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    artist_label: Gtk.Label = Gtk.Template.Child()

    # ActionRow widget
    list_view_row: Adw.ActionRow = Gtk.Template.Child()
    cover_img_row: Gtk.Image = Gtk.Template.Child()
    buttons_revealer_row: Gtk.Revealer = Gtk.Template.Child()
    play_button_row: Gtk.Button = Gtk.Template.Child()
    metadata_editor_button_row: Gtk.Button = Gtk.Template.Child()
    info_button_row: Gtk.Button = Gtk.Template.Child()

    # Metadata editor Dialog
    metadata_editor: Adw.Dialog = Gtk.Template.Child()
    metadata_editor_cancel_button: Gtk.Button = Gtk.Template.Child()
    metadata_editor_apply_button: Gtk.Button = Gtk.Template.Child()
    metadata_editor_cover_image: Gtk.Image = Gtk.Template.Child()
    metadata_editor_cover_button: Gtk.MenuButton = Gtk.Template.Child()
    metadata_editor_props: Gtk.ListBox = Gtk.Template.Child()
    metadata_editor_title_row: Adw.EntryRow = Gtk.Template.Child()
    metadata_editor_artist_row: Adw.EntryRow = Gtk.Template.Child()
    metadata_editor_album_row: Adw.EntryRow = Gtk.Template.Child()

    def __init__(self, file: Union[FileID3, FileVorbis]) -> None:
        super().__init__()

        self._file: Union[FileID3, FileVorbis] = file
        self._mde_new_cover_path: str = ""
        self.title_label.set_text(self.title)
        self.list_view_row.set_title(self.title)
        self.artist_label.set_text(self.artist)
        self.list_view_row.set_subtitle(self.artist)
        self.invalidate_cover(self.cover_img)
        self.invalidate_cover(self.cover_img_row)

        for seat in Gdk.Display.get_default().list_seats():
            if seat.get_capabilities() & Gdk.SeatCapabilities.TOUCH:
                long_gesture_controller = Gtk.GestureLongPress.new()
                self.add_controller(long_gesture_controller)
                long_gesture_controller.connect("pressed", self.toggle_buttons)
                long_gesture_controller_row = Gtk.GestureLongPress.new()
                self.list_view_row.add_controller(long_gesture_controller_row)
                long_gesture_controller_row.connect("pressed", self.toggle_buttons_row)
            else:
                event_controller_motion = Gtk.EventControllerMotion.new()
                self.add_controller(event_controller_motion)
                event_controller_motion.connect("enter", self.toggle_buttons)
                event_controller_motion.connect("leave", self.toggle_buttons)
                event_controller_motion_row = Gtk.EventControllerMotion.new()
                self.list_view_row.add_controller(event_controller_motion_row)
                event_controller_motion_row.connect("enter", self.toggle_buttons_row)
                event_controller_motion_row.connect("leave", self.toggle_buttons_row)
            break

        self.cover_button.connect("clicked", self.on_play_button_clicked)
        self.list_view_row.connect("activated", self.on_play_button_clicked)
        self.play_button.connect("clicked", self.on_play_button_clicked)
        self.play_button_row.connect("clicked", self.on_play_button_clicked)
        self.info_button.connect("clicked", self.gen_box_dialog)
        self.info_button_row.connect("clicked", self.gen_box_dialog)
        self.metadata_editor_button.connect("clicked", self.open_metadata_editor)
        self.metadata_editor_button_row.connect("clicked", self.open_metadata_editor)

        self.metadata_editor_apply_button.connect("clicked", self.metadata_editor_save)
        self.metadata_editor_cancel_button.connect(
            "clicked", self.on_metadata_editor_close
        )

        actions: Gio.SimpleActionGroup = Gio.SimpleActionGroup.new()
        change_action: Gio.SimpleAction = Gio.SimpleAction.new("change", None)
        change_action.connect("activate", self.metadata_change_cover)
        remove_action: Gio.SimpleAction = Gio.SimpleAction.new("remove", None)
        remove_action.connect("activate", self.metadata_remove_cover)
        actions.add_action(change_action)
        actions.add_action(remove_action)
        self.metadata_editor_cover_button.insert_action_group("card", actions)

    def on_play_button_clicked(self, *_args) -> None:
        """Opens sync page for `self` and media stream"""
        shared.win.loaded_card = self
        self.invalidate_cover(shared.win.sync_page_cover)
        shared.win.sync_page_title.set_text(self.title)
        shared.win.sync_page_artist.set_text(self.artist)
        mediastream = Gtk.MediaFile.new_for_filename(self._file.path)
        mediastream.connect("notify::timestamp", shared.win.on_timestamp_changed)
        shared.win.controls.set_media_stream(mediastream)
        shared.win.controls_shrinked.set_media_stream(mediastream)
        shared.win.navigation_view.push(shared.win.sync_navigation_page)
        if os.path.exists(
            file := shared.state_schema.get_string("opened-dir")
            + pathlib.Path(self._file.path).stem
            + shared.schema.get_string("auto-file-format")
        ) and shared.schema.get_boolean("auto-file-manipulation"):
            file_parser(file)

    def open_metadata_editor(self, *_args) -> None:
        """Prepares metadata editor and shows it"""
        if (texture := self._file.get_cover_texture()) != "icon":
            self.metadata_editor_cover_image.set_from_paintable(texture)
        else:
            self.metadata_editor_cover_image.set_from_icon_name("note-placeholder")
        (
            self.metadata_editor_title_row.set_text(self.title)
            if self._file.title is not None and self._file.title != ""
            else self.metadata_editor_title_row.set_text("")
        )
        (
            self.metadata_editor_artist_row.set_text(self.artist)
            if self._file.artist is not None and self._file.artist != ""
            else self.metadata_editor_artist_row.set_text("")
        )
        (
            self.metadata_editor_album_row.set_text(self.album)
            if self._file.album is not None and self._file.album != ""
            else self.metadata_editor_album_row.set_text("")
        )
        self.metadata_editor.present(shared.win)

    def metadata_editor_save(self, *_args) -> None:
        """Emits when Apply button of metadata editor pressed. Saves chages to file and updates the UI"""
        if (
            self._file._cover_updated
            and self._mde_new_cover_path != ""
            and self._mde_new_cover_path is not None
        ):
            self._file.set_cover(self._mde_new_cover_path)
            self._file._cover_updated = False
        elif (self._file._cover_updated) and (self._mde_new_cover_path is None):
            self._file.set_cover(None)
            self._file._cover_updated = False

        if (
            title_data := self.metadata_editor_title_row.get_text()
        ) != self._file.title:
            self._file.set_str_data("TIT2", title_data)
        if (
            artist_data := self.metadata_editor_artist_row.get_text()
        ) != self._file.artist:
            self._file.set_str_data("TPE1", artist_data)
        if (
            album_data := self.metadata_editor_album_row.get_text()
        ) != self._file.album:
            self._file.set_str_data("TALB", album_data)

        self._file.save()
        self.invalidate_cover(self.cover_img)
        self.invalidate_cover(self.cover_img_row)
        self.title_label.set_text(self.title)
        self.list_view_row.set_title(self.title)
        self.artist_label.set_text(self.artist)
        self.list_view_row.set_subtitle(self.artist)
        self.metadata_editor.close()

    def metadata_change_cover(self, *_args) -> None:
        """Presents new cover selection file dialog"""
        dialog = Gtk.FileDialog(
            default_filter=Gtk.FileFilter(mime_types=["image/png", "image/jpeg"])
        )
        dialog.open(shared.win, None, self.on_metadata_change_cover)

    def on_metadata_change_cover(
        self, dialog: Gtk.FileDialog, result: Gio.Task
    ) -> None:
        """Emits by `self.metadata_chage_cover` and sets new picture to unsaved changes

        Parameters
        ----------
        file_dialog : Gtk.FileDialog
            FileDialog which emited this function
        result : Gio.Task
            The result of the file selection
        """
        self._mde_new_cover_path = dialog.open_finish(result).get_path()
        self._file._cover_updated = True
        self.metadata_editor_cover_image.set_from_paintable(
            Gdk.Texture.new_from_filename(self._mde_new_cover_path)
        )

    def metadata_remove_cover(self, *_args) -> None:
        """Removes cover from the file and sets it to unsaved changes"""
        self._mde_new_cover_path = None
        self._file._cover_updated = True
        self.metadata_editor_cover_image.set_from_icon_name("note-placeholder")

    def on_metadata_editor_close(self, *_args) -> None:
        """Sets temporary changes variables to default"""
        self._file._cover_updated = False
        self._mde_new_cover_path = ""
        self.metadata_editor.close()

    def gen_box_dialog(self, *_args) -> None:
        """Generates and presents dialog with file metadata"""
        BoxDialog(
            label_str,
            (
                (title_str, self._file.title),
                (artist_str, self._file.artist),
                (album_str, self._file.album),
                (path_str, self._file.path),
            ),
        ).present(shared.win)

    def toggle_buttons(self, *_args) -> None:
        """Sets if buttons should be visible or not"""
        self.buttons_revealer.set_reveal_child(
            not self.buttons_revealer.get_reveal_child()
        )

    def toggle_buttons_row(self, *_args) -> None:
        """Sets if buttons should be visible or not"""
        self.buttons_revealer_row.set_reveal_child(
            not self.buttons_revealer_row.get_reveal_child()
        )

    def invalidate_cover(self, widget: Gtk.Image) -> None:
        """Sets image of the provided widget to `self.cover`

        Parameters
        ----------
        widget : Gtk.Image
            `Gtk.Image` widget to set cover to
        """
        if (_texture := self._file.get_cover_texture()) == "icon":
            widget.set_from_icon_name("note-placeholder")
        else:
            widget.set_from_paintable(_texture)

    def get_list_mode(self) -> Adw.ActionRow:
        """Returns `Adw.ActionRow` widget of the card for list view mode

        Returns
        -------
        Adw.ActionRow
            `Adw.ActionRow` copy of the `self` widget
        """
        return self.list_view_row

    @property
    def title(self) -> str:
        if self._file.title is None or self._file.title == "":
            return os.path.basename(self._file.path)
        return self._file.title

    @title.setter
    def title(self, value: str):
        self._file.title = value
        if value is None or value == "":
            self.title_label.set_text(_("Unknown"))
            self.list_view_row.set_title(_("Unknown"))
        else:
            self.title_label.set_text(value)
            self.list_view_row.set_title(value)

    @property
    def artist(self) -> str:
        if self._file.artist is None or self._file.artist == "":
            return _("Unknown")
        return self._file.artist

    @artist.setter
    def artist(self, value: str):
        self._file.artist = value
        if value is None or value == "":
            self.artist_label.set_text(_("Unknown"))
            self.list_view_row.set_subtitle(_("Unknown"))
        else:
            self.artist_label.set_text(value)
            self.list_view_row.set_subtitle(value)

    @GObject.Property(type=str)
    def album(self) -> str:
        if self._file.album is None or self._file.album == "":
            return _("Unknown")
        return self._file.album

    @album.setter
    def album(self, value: str):
        self._file.album = value

    @property
    def cover(self) -> Union[str, bytes]:
        return self._file.cover

    @cover.setter
    def cover(self, value: Union[bytes, str]) -> None:
        if type(value) == bytes or type(value) == str:
            self._file.cover = value
            if type(value) == bytes:
                self.cover_img.set_from_paintable(self._file.get_cover_texture())
                self.cover_img_row.set_from_paintable(self._file.get_cover_texture())
            else:
                self.cover_img.set_from_icon_name("note-placeholder")
                self.cover_img_row.set_from_icon_name("note-placeholder")
        else:
            raise ValueError("Cover must be bytes or str")

    @property
    def duration(self) -> int:
        return self._file.duration
