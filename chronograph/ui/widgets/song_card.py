from typing import Optional

from gi.repository import Gdk, GObject, Gtk

from chronograph.backend.file.song_card_model import SongCardModel
from chronograph.internal import Constants
from chronograph.ui.dialogs.about_file_dialog import AboutFileDialog
from chronograph.ui.dialogs.metadata_editor import MetadataEditor
from dgutils import Linker

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/SongCard.ui")
class SongCard(Gtk.Box, Linker):
  __gtype_name__ = "SongCard"

  buttons_revealer: Gtk.Revealer = gtc()
  play_button: Gtk.Button = gtc()
  metadata_editor_button: Gtk.Button = gtc()
  info_button: Gtk.Button = gtc()
  cover_button: Gtk.Button = gtc()
  cover_loading_stack: Gtk.Stack = gtc()
  cover_placeholder: Gtk.Image = gtc()
  cover_img: Gtk.Image = gtc()
  detele_icon_img: Gtk.Image = gtc()
  title_label: Gtk.Label = gtc()
  artist_label: Gtk.Label = gtc()

  def __init__(self) -> None:
    super().__init__()
    Linker.__init__(self)
    self._bulk_selected = False

    self.event_controller_motion = Gtk.EventControllerMotion.new()
    self.add_controller(self.event_controller_motion)

  def bind(self, model: SongCardModel) -> None:
    """Bind a model and connect UI signal handlers.

    Parameters
    ----------
    model : SongCardModel
      Model to display and interact with.
    """
    self._model = model
    # Bind properties
    self.new_binding(
      model.bind_property(
        "title_display", self.title_label, "label", GObject.BindingFlags.SYNC_CREATE
      )
    )
    self.new_binding(
      model.bind_property(
        "artist_display", self.artist_label, "label", GObject.BindingFlags.SYNC_CREATE
      )
    )
    self.new_binding(model.bind_property("cover", self.cover_img, "paintable"))

    # Connect motion controller
    self.new_connection(self.event_controller_motion, "enter", self._toggle_buttons)
    self.new_connection(self.event_controller_motion, "leave", self._toggle_buttons)

    # Connect buttons
    self.new_connection(self.play_button, "clicked", self._load, model)
    self.new_connection(self.info_button, "clicked", self._show_info, model)
    self.new_connection(
      self.metadata_editor_button, "clicked", self._open_metadata_editor, model
    )

    # Connect main cover button
    self.new_connection(self.cover_button, "clicked", self._load, model)

  def unbind(self) -> None:
    """Clear bindings and release model references."""
    self.set_cover(None)
    self._model = None
    self.link_teardown()

  def set_cover(self, cover: Optional[Gdk.Texture] = None) -> None:
    """Update the cover image and placeholder state.

    Parameters
    ----------
    cover : Optional[Gdk.Texture], optional
      Cover texture to display, or None to show placeholder.
    """
    if cover is not None:
      self.cover_img.set_from_paintable(cover)
    else:
      self.cover_img.set_from_paintable(None)
    if self._bulk_selected:
      return
    if cover is not None:
      self.cover_loading_stack.set_visible_child(self.cover_img)
    else:
      self.cover_loading_stack.set_visible_child(self.cover_placeholder)

  def set_bulk_selected(self, selected: bool) -> None:
    """Toggle bulk selection visual state.

    Parameters
    ----------
    selected : bool
      Whether the card is selected in bulk mode.
    """
    self._bulk_selected = selected
    if selected:
      self.cover_button.add_css_class("bulk-delete-selected")
      self.cover_loading_stack.set_visible_child(self.detele_icon_img)
    else:
      self.cover_button.remove_css_class("bulk-delete-selected")
      if self.cover_img.get_paintable() is not None:
        self.cover_loading_stack.set_visible_child(self.cover_img)
      else:
        self.cover_loading_stack.set_visible_child(self.cover_placeholder)

  def _load(self, _btn, model: SongCardModel) -> None:
    if Constants.WIN.is_bulk_delete_mode():
      Constants.WIN.library.toggle_bulk_selection(self, model)
      return
    Constants.WIN.enter_sync_mode(model)

  def _show_info(self, _btn, model: SongCardModel) -> None:
    AboutFileDialog(model).present(Constants.WIN)

  def _open_metadata_editor(self, _btn, model: SongCardModel) -> None:
    MetadataEditor(model).present(Constants.WIN)

  def _toggle_buttons(self, *_args) -> None:
    self.buttons_revealer.set_reveal_child(not self.buttons_revealer.get_reveal_child())
