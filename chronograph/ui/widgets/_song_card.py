from typing import Optional

from gi.repository import Gdk, GObject, Gtk

from chronograph.backend.file._song_card_model import SongCardModel
from chronograph.internal import Constants
from dgutils import Linker

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/_SongCard.ui")
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
  title_label: Gtk.Label = gtc()
  artist_label: Gtk.Label = gtc()
  lyrics_state_indicator: Gtk.Button = gtc()

  def __init__(self) -> None:
    super().__init__()
    Linker.__init__(self)

    self.event_controller_motion = Gtk.EventControllerMotion.new()
    self.add_controller(self.event_controller_motion)

  def bind(self, model: SongCardModel) -> None:
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
    self.set_cover(None)
    self.link_teardown()

  def set_cover(self, cover: Optional[Gdk.Texture] = None) -> None:
    if cover:
      self.cover_img.set_from_paintable(cover)
      self.cover_loading_stack.set_visible_child(self.cover_img)
    else:
      self.cover_loading_stack.set_visible_child(self.cover_placeholder)
      self.cover_img.set_from_paintable(None)

  # TODO:
  def _load(self, _btn, model: SongCardModel) -> None:
    pass

  # TODO:
  def _show_info(self, _btn, model: SongCardModel) -> None:
    pass

  # TODO:
  def _open_metadata_editor(self, _btn, model: SongCardModel) -> None:
    pass

  def _toggle_buttons(self, *_args) -> None:
    self.buttons_revealer.set_reveal_child(not self.buttons_revealer.get_reveal_child())
