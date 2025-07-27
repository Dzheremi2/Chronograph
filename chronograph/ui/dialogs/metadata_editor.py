from typing import Optional

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from chronograph.internal import Constants

gtc = Gtk.Template.Child  # pylint: disable=invalid-name
logger = Constants.LOGGER


@Gtk.Template.from_resource(Constants.PREFIX + "/gtk/ui/dialogs/MetadataEditor.ui")
class MetadataEditor(Adw.Dialog):
    __gtype_name__ = "MetadataEditor"

    cover_image: Gtk.Image = gtc()
    title_row: Adw.EntryRow = gtc()
    artist_row: Adw.EntryRow = gtc()
    album_row: Adw.EntryRow = gtc()

    def __init__(self, card) -> "MetadataEditor":
        super().__init__()
        self._is_cover_changed: bool = False
        self._new_cover_path: Optional[str] = ""
        self._card = card
        self.title_row.set_text(self._card.title)
        self.artist_row.set_text(self._card.artist)
        self._card.bind_property(
            "cover", self.cover_image, "paintable", GObject.BindingFlags.SYNC_CREATE
        )
        self.album_row.set_text(self._card.album)

        _actions = Gio.SimpleActionGroup.new()
        _change_action = Gio.SimpleAction.new("change", None)
        _change_action.connect("activate", self._change_cover)
        _remove_action = Gio.SimpleAction.new("remove", None)
        _remove_action.connect("activate", self._remove_cover)
        _actions.add_action(_change_action)
        _actions.add_action(_remove_action)
        self.insert_action_group("cover", _actions)

    @Gtk.Template.Callback()
    def on_cancel_clicked(self, *_args) -> None:
        """Handle cancel button click"""
        self.close()
        logger.debug("Metadata Editor(%s) closed", self)

    @Gtk.Template.Callback()
    def save(self, *_args) -> None:
        """Save metadata changes"""
        if self._is_cover_changed:
            # pylint: disable=protected-access
            self._card._file.set_cover(self._new_cover_path)
            self._card.cover_img.set_from_paintable(self._card.cover)
            pspec = self._card.__class__.find_property("cover")
            self._card.emit("notify::cover", pspec)
            logger.info(
                "Cover for '%s -- %s / %s' was saved",
                self._card.title_display,
                self._card.artist_display,
                self._card.album_display,
            )
        if self.title_row.get_text() != self._card.title and self.title_row.get_text():
            self._card.title = self.title_row.get_text()
            logger.info(
                "Title for '%s -- %s / %s' was saved",
                self._card.title_display,
                self._card.artist_display,
                self._card.album_display,
            )
        if (
            self.artist_row.get_text() != self._card.artist
            and self.artist_row.get_text()
        ):
            self._card.artist = self.artist_row.get_text()
            logger.info(
                "Artist for '%s -- %s / %s' was saved",
                self._card.title_display,
                self._card.artist_display,
                self._card.album_display,
            )
        if self.album_row.get_text() != self._card.album and self.album_row.get_text():
            self._card.album = self.album_row.get_text()
            logger.info(
                "Album for '%s -- %s / %s' was saved",
                self._card.title_display,
                self._card.artist_display,
                self._card.album_display,
            )
        self._card.save()
        self.close()

    def _change_cover(self, *_args) -> None:

        def _on_change_cover(dialog: Gtk.FileDialog, result: Gio.Task) -> None:
            self._new_cover_path = dialog.open_finish(result).get_path()
            self._is_cover_changed = True
            self.cover_image.set_from_paintable(
                Gdk.Texture.new_from_filename(self._new_cover_path)
            )
            logger.debug("Queuing cover changing to '%s' image", self._new_cover_path)

        dialog = Gtk.FileDialog(
            default_filter=Gtk.FileFilter(mime_types=["image/png", "image/jpeg"])
        )
        dialog.open(Constants.WIN, None, _on_change_cover)

    def _remove_cover(self, *_args) -> None:
        self._is_cover_changed = True
        self._new_cover_path = None
        self.cover_image.set_from_paintable(Constants.COVER_PLACEHOLDER)
        logger.debug(
            "Queuing cover removing for '%s -- %s / %s'",
            self._card.title_display,
            self._card.artist_display,
            self._card.album_display,
        )
