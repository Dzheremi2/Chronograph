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

    buttons_revealer: Gtk.Revealer = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    metadata_editor_button: Gtk.Button = Gtk.Template.Child()
    info_button: Gtk.Button = Gtk.Template.Child()
    cover_button: Gtk.Button = Gtk.Template.Child()
    cover_img: Gtk.Image = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    artist_label: Gtk.Label = Gtk.Template.Child()

    # Metadata editor
    metadata_editor: Adw.Dialog = Gtk.Template.Child()
    metadata_editor_cover_button: Gtk.MenuButton = Gtk.Template.Child()
    metadata_editor_cover_image: Gtk.Image = Gtk.Template.Child()
    metadata_editor_title_row: Adw.EntryRow = Gtk.Template.Child()
    metadata_editor_artist_row: Adw.EntryRow = Gtk.Template.Child()
    metadata_editor_album_row: Adw.EntryRow = Gtk.Template.Child()
    metadata_editor_apply_button: Gtk.Button = Gtk.Template.Child()
    metadata_editor_cancel_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, file: Union[FileID3, FileVorbis]) -> None:
        super().__init__()
        self._file: Union[FileID3, FileVorbis] = file
        self._mde_new_cover_path: str = ""
        self.title_label.set_text(self._file.title)
        self.artist_label.set_text(self._file.artist)

        for seat in Gdk.Display.get_default().list_seats():
            if seat.get_capabilities() & Gdk.SeatCapabilities.TOUCH:
                long_gesture_controller = Gtk.GestureLongPress.new()
                self.add_controller(long_gesture_controller)
                long_gesture_controller.connect("pressed", self.toggle_buttons)
            else:
                event_controller_motion = Gtk.EventControllerMotion.new()
                self.add_controller(event_controller_motion)
                event_controller_motion.connect("enter", self.toggle_buttons)
                event_controller_motion.connect("leave", self.toggle_buttons)
            break
        self.metadata_editor_button.connect("clicked", self.open_metadata_editor)
        self.metadata_editor_apply_button.connect("clicked", self.metadata_editor_save)
        self.metadata_editor_cancel_button.connect(
            "clicked", self.on_metadata_editor_close
        )
        self.metadata_editor_apply_button.connect("clicked", self.metadata_editor_save)
        self.info_button.connect(
            "clicked",
            lambda *_: BoxDialog(
                label_str,
                (
                    (title_str, self.title),
                    (artist_str, self.artist),
                    (album_str, self.album),
                    (path_str, self._file.path),
                ),
            ).present(shared.win),
        )
        self.cover_button.connect("clicked", self.on_play_button_clicked)
        self.play_button.connect("clicked", self.on_play_button_clicked)
        self.bind_props()
        self.invalidate_cover(self.cover_img)

        actions: Gio.SimpleActionGroup = Gio.SimpleActionGroup.new()
        change_action: Gio.SimpleAction = Gio.SimpleAction.new("change", None)
        change_action.connect("activate", self.metadata_change_cover)
        remove_action: Gio.SimpleAction = Gio.SimpleAction.new("remove", None)
        remove_action.connect("activate", self.metadata_remove_cover)
        actions.add_action(change_action)
        actions.add_action(remove_action)
        self.metadata_editor_cover_button.insert_action_group("card", actions)

    def open_metadata_editor(self, *_args) -> None:
        """Prepares metadata editor and shows it"""
        if (texture := self._file.get_cover_texture()) != "icon":
            self.metadata_editor_cover_image.set_from_paintable(texture)
        else:
            self.metadata_editor_cover_image.set_from_icon_name("note-placeholder")
        (
            self.metadata_editor_title_row.set_text(self.title)
            if self.title != "Unknоwn"
            else self.metadata_editor_title_row.set_text("")
        )
        (
            self.metadata_editor_artist_row.set_text(self.artist)
            if self.artist != "Unknоwn"
            else self.metadata_editor_artist_row.set_text("")
        )
        (
            self.metadata_editor_album_row.set_text(self.album)
            if self.album != "Unknоwn"
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

        if (title_data := self.metadata_editor_title_row.get_text()) != self.title:
            self._file.set_str_data("TIT2", title_data)
        if (artist_data := self.metadata_editor_artist_row.get_text()) != self.artist:
            self._file.set_str_data("TPE1", artist_data)
        if (album_data := self.metadata_editor_album_row.get_text()) != self.album:
            self._file.set_str_data("TALB", album_data)

        self._file.save()
        self.invalidate_cover(self.cover_img)
        self.invalidate_update("title")
        self.invalidate_update("artist")
        self.metadata_editor.close()

    def metadata_change_cover(self, *_args) -> None:
        """Presents new cover selection file dialog"""
        dialog = Gtk.FileDialog(
            default_filter=Gtk.FileFilter(mime_types=["image/png", "image/jpeg"])
        )
        dialog.open(shared.win, None, self.on_metadata_change_cover)

    def on_metadata_change_cover(
        self, file_dialog: Gtk.FileDialog, result: Gio.Task
    ) -> None:
        """Emits by `self.metadata_chage_cover` and sets new picture to unsaved changes

        Parameters
        ----------
        file_dialog : Gtk.FileDialog
            FileDialog which emited this function
        result : Gio.Task
            The result of the file selection
        """
        self._mde_new_cover_path = file_dialog.open_finish(result).get_path()
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

    def toggle_buttons(self, *_args) -> None:
        """Sets if buttons should be visible or not"""
        self.buttons_revealer.set_reveal_child(
            not self.buttons_revealer.get_reveal_child()
        )

    def invalidate_update(self, property: str, scope: str = "self") -> None:
        """Automatically updates interface labels on property change

        Parameters
        ----------
        property : str
            name of propety in `chronograph.utils.file.BaseFile` which triggers update
        scope : str, optional
            scope of update, by default `self`, may be `sync_page` (`chronograph.ChronographWindow.sync_page`)
        """
        if scope == "self":
            getattr(self, f"{property}_label").set_text(getattr(self, f"{property}"))
        elif scope == "sync_page":
            getattr(shared.win, f"sync_page_{property}").set_text(
                getattr(self, f"{property}")
            )

    def invalidate_cover(self, widget: Gtk.Image) -> None:
        """Automatically updates cover on property change"""
        if (_texture := self._file.get_cover_texture()) == "icon":
            widget.set_from_icon_name("note-placeholder")
        else:
            widget.set_from_paintable(_texture)

    def bind_props(self) -> None:
        """Binds properties to update interface labels on change"""
        self.connect(
            "notify::title",
            lambda _object, property: self.invalidate_update(property.name),
        )
        self.connect(
            "notify::artist",
            lambda _object, property: self.invalidate_update(property.name),
        )
        self.connect("notify::cover", lambda *_: self.invalidate_cover(self.cover_img))

    def on_play_button_clicked(self, *_args) -> None:
        """Opens sync page for `self` and media stream"""
        shared.win.loaded_card = self
        self.invalidate_cover(shared.win.sync_page_cover)
        self.invalidate_update("title", "sync_page")
        self.invalidate_update("artist", "sync_page")
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

    @GObject.Property(type=str)
    def title(self) -> str:
        return self._file.title

    @title.setter
    def title(self, value: str) -> None:
        self._file.title = value

    @GObject.Property(type=str)
    def artist(self) -> str:
        return self._file.artist

    @artist.setter
    def artist(self, value: str) -> None:
        self._file.artist = value

    @GObject.Property(type=str)
    def album(self) -> str:
        return self._file.album

    @album.setter
    def album(self, value: str) -> None:
        self._file.album = value

    @GObject.Property
    def cover(self) -> Union[str, bytes]:
        return self._file.cover

    @cover.setter
    def cover(self, data: bytes) -> None:
        if type(data) == bytes:
            self._file.cover = data
        else:
            raise ValueError("Cover must be bytes")

    @property
    def duration(self) -> int:
        return self._file.duration

    @property
    def album(self) -> str:
        return self._file._album
