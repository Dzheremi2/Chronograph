from gettext import pgettext as C_
from pathlib import Path

from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.internal import Constants
from chronograph.ui.dialogs.box_dialog import BoxDialog
from chronograph.ui.dialogs.metadata_editor import MetadataEditor
from chronograph.utils.file_backend import SongCardModel
from chronograph.utils.lyrics import LyricsFormat
from chronograph.utils.media import FileUntaggable

gtc = Gtk.Template.Child
logger = Constants.LOGGER


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/SongCard.ui")
class SongCard(Gtk.Box):
  __gtype_name__ = "SongCard"

  buttons_revealer: Gtk.Revealer = gtc()
  play_button: Gtk.Button = gtc()
  metadata_editor_button: Gtk.Button = gtc()
  info_button: Gtk.Button = gtc()
  cover_button: Gtk.Button = gtc()
  cover_img: Gtk.Image = gtc()
  title_label: Gtk.Label = gtc()
  artist_label: Gtk.Label = gtc()
  lyrics_state_indicator: Gtk.Button = gtc()

  list_view_row: Adw.ActionRow = gtc()
  cover_img_row: Gtk.Image = gtc()
  lyrics_state_indicator_row: Gtk.Button = gtc()
  buttons_revealer_row: Gtk.Revealer = gtc()
  row_metadata_editor_button: Gtk.Button = gtc()

  def __init__(self, model: SongCardModel) -> None:
    super().__init__()
    self.model = model
    # Setup UI reactivity
    self.model.bind_property(
      "title_display",
      self.title_label,
      "label",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.model.bind_property(
      "title_display",
      self.list_view_row,
      "title",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.model.bind_property(
      "artist_display",
      self.artist_label,
      "label",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.model.bind_property(
      "artist_display",
      self.list_view_row,
      "subtitle",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.cover_img.set_from_paintable(self.model.cover)
    self.model.bind_property(
      "cover",
      self.cover_img,
      "paintable",
      GObject.BindingFlags.DEFAULT,
    )
    self.model.bind_property(
      "cover",
      self.cover_img_row,
      "paintable",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.model.bind_property(
      "lyrics_format",
      self.lyrics_state_indicator,
      "label",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.model.bind_property(
      "lyrics_format",
      self.lyrics_state_indicator_row,
      "label",
      GObject.BindingFlags.SYNC_CREATE,
    )
    # Call for initial state
    self._on_lyr_format_changed(None, self.model.lyrics_file.highest_format)
    self.model.connect("lyr-format-changed", self._on_lyr_format_changed)

    # Setup buttons interaction
    self.event_controller_motion = Gtk.EventControllerMotion.new()
    self.add_controller(self.event_controller_motion)
    self.event_controller_motion.connect("enter", self._toggle_buttons)
    self.event_controller_motion.connect("leave", self._toggle_buttons)
    event_controller_motion_row = Gtk.EventControllerMotion.new()
    self.list_view_row.add_controller(event_controller_motion_row)
    event_controller_motion_row.connect("enter", self._toggle_buttons_row)
    event_controller_motion_row.connect("leave", self._toggle_buttons_row)

    if isinstance(self.model.mfile, FileUntaggable):
      self.metadata_editor_button.set_visible(False)
      self.row_metadata_editor_button.set_visible(False)

  @Gtk.Template.Callback()
  def load(self, *_args) -> None:
    Constants.WIN.enter_sync_mode(self.model)

  @Gtk.Template.Callback()
  def show_info(self, *_args) -> None:
    """Shows song info dialog"""
    BoxDialog(
      C_("song info dialog", "About File"),
      (
        {
          "title": _("Title"),
          "subtitle": self.model.title_display,
        },
        {
          "title": _("Artist"),
          "subtitle": self.model.artist_display,
        },
        {"title": _("Album"), "subtitle": self.model.album_display},
        {
          "title": _("Path"),
          "subtitle": self.model.path,
          "action": {
            "icon": "open-source-symbolic",
            "tooltip": _("Show"),
            "callback": lambda _: Gio.AppInfo.launch_default_for_uri(
              f"file://{Path(self.model.path).parent}"
            ),
          },
        },
      ),
    ).present(Constants.WIN)
    logger.debug(
      "File info dialog for '%s -- %s' was shown",
      self.model.title_display,
      self.model.artist_display,
    )

  @Gtk.Template.Callback()
  def open_metadata_editor(self, *_args) -> None:
    """Open metadata editor dialog"""
    logger.debug(
      "Opening metadata editor for '%s -- %s'",
      self.model.title_display,
      self.model.artist_display,
    )
    MetadataEditor(self.model).present(Constants.WIN)

  def get_list_mode(self) -> Adw.ActionRow:
    return self.list_view_row

  def _toggle_buttons(self, *_args) -> None:
    self.buttons_revealer.set_reveal_child(not self.buttons_revealer.get_reveal_child())

  def _toggle_buttons_row(self, *_args) -> None:
    self.buttons_revealer_row.set_visible(not self.buttons_revealer_row.get_visible())

  def _on_lyr_format_changed(self, _model, lyrics_fmt: int) -> None:
    match lyrics_fmt:
      case LyricsFormat.NONE.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "none"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "none"]
        )
      case LyricsFormat.PLAIN.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "plain"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "plain"]
        )
      case LyricsFormat.LRC.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "lrc"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "lrc"]
        )
      case LyricsFormat.ELRC.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "elrc"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "elrc"]
        )
