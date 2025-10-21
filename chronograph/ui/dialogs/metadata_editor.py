from typing import Optional

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from chronograph.internal import Constants
from chronograph.ui.widgets.internal.menu_button import ChrMenuButton  # noqa: F401
from chronograph.utils.file_backend import SongCardModel
from chronograph.utils.lyrics import Lyrics
from dgutils import Actions

gtc = Gtk.Template.Child
logger = Constants.LOGGER


@Gtk.Template.from_resource(Constants.PREFIX + "/gtk/ui/dialogs/MetadataEditor.ui")
@Actions.from_schema(Constants.PREFIX + "/resources/actions/metadata_editor.yaml")
class MetadataEditor(Adw.Dialog):
  __gtype_name__ = "MetadataEditor"

  cover_image_bin: Adw.Bin = gtc()
  edit_icon_revealer: Gtk.Revealer = gtc()
  cover_image: Gtk.Image = gtc()
  title_row: Adw.EntryRow = gtc()
  artist_row: Adw.EntryRow = gtc()
  album_row: Adw.EntryRow = gtc()
  lyrics_buttons_box: Gtk.Box = gtc()

  def __init__(self, card_model: SongCardModel) -> None:
    from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
    from chronograph.ui.sync_pages.wbw_sync_page import WBWSyncPage

    super().__init__()
    self._is_cover_changed: bool = False
    self._new_cover_path: Optional[str] = ""
    self._card = card_model
    self.title_row.set_text(self._card.title)
    self.artist_row.set_text(self._card.artist)
    self._card.bind_property(
      "cover", self.cover_image, "paintable", GObject.BindingFlags.SYNC_CREATE
    )
    self.album_row.set_text(self._card.album)

    self.hover_controller = Gtk.EventControllerMotion.new()
    self.hover_controller.connect("enter", self._on_icon_revealer)
    self.hover_controller.connect("leave", self._on_icon_revealer)
    self.cover_image_bin.add_controller(self.hover_controller)

    # Hide "Embed Lyrics" button if launched from library page
    page = Constants.WIN.navigation_view.get_visible_page()
    if not isinstance(page, (WBWSyncPage, LRCSyncPage)):
      self.lyrics_buttons_box.set_visible(False)

  @Gtk.Template.Callback()
  def on_cancel_clicked(self, *_args) -> None:
    """Handle cancel button click"""
    self.close()
    logger.debug("Metadata Editor(%s) closed", self)

  @Gtk.Template.Callback()
  def on_embed_lyrics_clicked(self, *_args) -> None:
    """Embedding lyrics to the file on button click"""
    from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
    from chronograph.ui.sync_pages.wbw_sync_page import WBWSyncPage

    page = Constants.WIN.navigation_view.get_visible_page()
    if isinstance(page, WBWSyncPage):
      if (
        page.modes.get_page(page.modes.get_visible_child()) == page.edit_view_stack_page
      ):
        lyrics = Lyrics(
          page.edit_view_text_view.get_buffer().get_text(
            page.edit_view_text_view.get_buffer().get_start_iter(),
            page.edit_view_text_view.get_buffer().get_end_iter(),
            include_hidden_chars=False,
          )
        )
      else:
        lyrics = Lyrics.from_tokens(page._lyrics_model.get_tokens())  # noqa: SLF001
      self._card.mfile.embed_lyrics(lyrics, force=True)
    elif isinstance(page, LRCSyncPage):
      lyrics = [line.get_text() for line in page.sync_lines]
      lyrics = Lyrics("\n".join(lyrics).strip())
      self._card.mfile.embed_lyrics(lyrics, force=True)
    else:
      logger.debug("Prevented lyrics embedding from library page")

  @Gtk.Template.Callback()
  def on_delete_lyrics_clicked(self, *_args) -> None:
    self._card.mfile.embed_lyrics(None)

  @Gtk.Template.Callback()
  def save(self, *_args) -> None:
    """Save metadata changes"""
    if self._is_cover_changed:
      self._card.mfile.set_cover(self._new_cover_path)
      self._card.widget.cover_img.set_from_paintable(self._card.cover)
      self._card.notify("cover")
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
    if self.artist_row.get_text() != self._card.artist and self.artist_row.get_text():
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

  def _on_icon_revealer(self, *_args) -> None:
    self.edit_icon_revealer.set_reveal_child(
      not self.edit_icon_revealer.get_reveal_child()
    )
