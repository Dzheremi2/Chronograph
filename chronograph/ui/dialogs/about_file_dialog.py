from gi.repository import Adw, GObject, Gtk

from chronograph.backend.file._song_card_model import SongCardModel
from chronograph.backend.file.library_manager import LibraryManager
from chronograph.internal import Constants
from dgutils import Linker

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/AboutFileDialog.ui")
class AboutFileDialog(Adw.Dialog, Linker):
  __gtype_name__ = "AboutFileDialog"

  nav_view: Adw.NavigationView = gtc()
  main_nav_page: Adw.NavigationPage = gtc()
  lyr_nav_page: Adw.NavigationPage = gtc()

  cover_image: Gtk.Image = gtc()
  title_info_row: Adw.ActionRow = gtc()
  artist_info_row: Adw.ActionRow = gtc()
  album_info_row: Adw.ActionRow = gtc()
  import_info_row: Adw.ActionRow = gtc()
  modified_info_row: Adw.ActionRow = gtc()
  available_lyrics_button: Adw.ActionRow = gtc()
  save_button: Gtk.Button = gtc()

  def __init__(self, model: SongCardModel) -> None:
    super().__init__()
    Linker.__init__(self)
    self._model = model
    self.available_lyrics_button.connect(
      "activated", self._on_available_lyrics_button_clicked
    )

    self.new_binding(
      self._model.bind_property(
        "cover", self.cover_image, "paintable", GObject.BindingFlags.SYNC_CREATE
      )
    )
    self.new_binding(
      self._model.bind_property(
        "title_display",
        self.title_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "artist_display",
        self.artist_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "album_display",
        self.album_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "imported_at",
        self.import_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "last_modified",
        self.modified_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )

  def close(self) -> bool:
    self.unbind_all()
    self._model = None
    super().close()

  def _on_available_lyrics_button_clicked(self, *_args) -> None:
    self.nav_view.push(self.lyr_nav_page)

  @Gtk.Template.Callback()
  def _on_delete_file_button_clicked(self, *_args) -> None:
    track_uuid: str = self._model.uuid
    title: str = self._model.title_display
    artist: str = self._model.artist_display

    LibraryManager.delete_files([track_uuid])

    cards_model = Constants.WIN.library.cards_model
    for index in range(cards_model.get_n_items()):
      card: SongCardModel = cards_model.get_item(index)
      if card is not None and card.uuid == track_uuid:
        cards_model.remove(index)
        break

    Constants.WIN.library.card_filter_model.notify("n-items")
    Constants.WIN.show_toast(
      _('File "{title} — {artist}" was deleted').format(title=title, artist=artist), 2
    )
    self.close()
