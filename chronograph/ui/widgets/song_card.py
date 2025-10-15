from gettext import pgettext as C_
from pathlib import Path
from typing import Union

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from chronograph.internal import Constants
from chronograph.ui.dialogs.box_dialog import BoxDialog
from chronograph.ui.dialogs.metadata_editor import MetadataEditor
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable
from chronograph.utils.lyrics import LyricsFile, LyricsFormat

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

  def __init__(
    self,
    file: Union[FileID3, FileVorbis, FileMP4, FileUntaggable],
    lyrics_file: LyricsFile,
  ) -> None:
    super().__init__()
    self._file = file
    self._lyrics_file = lyrics_file
    self.bind_property(
      "title_display",
      self.title_label,
      "label",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.bind_property(
      "title_display",
      self.list_view_row,
      "title",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.bind_property(
      "artist_display",
      self.artist_label,
      "label",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.bind_property(
      "artist_display",
      self.list_view_row,
      "subtitle",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.cover_img.set_from_paintable(self.cover)
    self.bind_property(
      "cover", self.cover_img, "paintable", GObject.BindingFlags.DEFAULT
    )
    self.bind_property(
      "cover", self.cover_img_row, "paintable", GObject.BindingFlags.SYNC_CREATE
    )

    self._on_lyrics_format_changed(self._lyrics_file, None)
    self._lyrics_file.connect("notify::highest-format", self._on_lyrics_format_changed)

    self.event_controller_motion = Gtk.EventControllerMotion.new()
    self.add_controller(self.event_controller_motion)
    self.event_controller_motion.connect("enter", self._toggle_buttons)
    self.event_controller_motion.connect("leave", self._toggle_buttons)
    event_controller_motion_row = Gtk.EventControllerMotion.new()
    self.list_view_row.add_controller(event_controller_motion_row)
    event_controller_motion_row.connect("enter", self._toggle_buttons_row)
    event_controller_motion_row.connect("leave", self._toggle_buttons_row)

    if isinstance(file, FileUntaggable):
      self.metadata_editor_button.set_visible(False)
      self.row_metadata_editor_button.set_visible(False)

  def _on_lyrics_format_changed(self, lyrics_file: LyricsFile, _pspec) -> None:
    match lyrics_file.highest_format:
      case LyricsFormat.NONE.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "none"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "none"]
        )
        self.lyrics_state_indicator.set_label(C_("means lyrics absence", "None"))
      case LyricsFormat.PLAIN.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "plain"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "plain"]
        )
        self.lyrics_state_indicator.set_label(_("Plain"))
      case LyricsFormat.LRC.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "lrc"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "lrc"]
        )
        self.lyrics_state_indicator.set_label("LRC")
      case LyricsFormat.ELRC.value:
        self.lyrics_state_indicator.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "elrc"]
        )
        self.lyrics_state_indicator_row.set_css_classes(
          ["no-hover", "pill", "small", "lyrics", "elrc"]
        )
        self.lyrics_state_indicator.set_label("eLRC")

  def _toggle_buttons(self, *_args) -> None:
    self.buttons_revealer.set_reveal_child(not self.buttons_revealer.get_reveal_child())

  def _toggle_buttons_row(self, *_args) -> None:
    self.buttons_revealer_row.set_visible(not self.buttons_revealer_row.get_visible())

  @Gtk.Template.Callback()
  def load(self, *_args) -> None:
    Constants.WIN.enter_sync_mode(self, self._file)

  @Gtk.Template.Callback()
  def show_info(self, *_args) -> None:
    """Show song info dialog"""
    BoxDialog(
      C_("song info dialog", "About File"),
      (
        {
          "title": _("Title"),
          "subtitle": self.title_display,
        },
        {
          "title": _("Artist"),
          "subtitle": self.artist_display,
        },
        {"title": _("Album"), "subtitle": self.album_display},
        {
          "title": _("Path"),
          "subtitle": self.path,
          "action": {
            "icon": "open-source-symbolic",
            "tooltip": _("Show"),
            "callback": lambda _: Gio.AppInfo.launch_default_for_uri(
              f"file://{Path(self.path).parent}"
            ),
          },
        },
      ),
    ).present(Constants.WIN)
    logger.debug(
      "File info dialog for '%s -- %s' was shown",
      self.title_display,
      self.artist_display,
    )

  @Gtk.Template.Callback()
  def open_metadata_editor(self, *_args) -> None:
    """Open metadata editor dialog"""
    logger.debug(
      "Opening metadata editor for '%s -- %s'",
      self.title_display,
      self.artist_display,
    )
    MetadataEditor(self).present(Constants.WIN)

  def save(self) -> None:
    """Save changes to the file"""
    self._file.save()

  def get_list_mode(self) -> Adw.ActionRow:
    return self.list_view_row

  def get_title(self) -> str:
    return self.title_display

  # A workaround for unificating invalidate_filter functions
  def get_subtitle(self) -> str:
    return self.artist_display

  @GObject.Property(type=str, default="")
  def title(self) -> str:
    """Title of the song"""
    return self._file.title or ""

  @title.setter
  def title(self, value: str) -> None:
    self._file.set_str_data("TIT2", value or "")
    self.notify("title_display")

  @GObject.Property(type=str, default="")
  def artist(self) -> str:
    """Artist of the song"""
    return self._file.artist or ""

  @artist.setter
  def artist(self, value: str) -> None:
    self._file.set_str_data("TPE1", value or "")
    self.notify("artist_display")

  @GObject.Property(type=str, default="")
  def album(self) -> str:
    """Album of the song"""
    return self._file.album or ""

  @album.setter
  def album(self, value: str) -> None:
    self._file.set_str_data("TALB", value or "")
    self.notify("album_display")

  @GObject.Property(type=str, default=C_("song title placeholder", "Unknown"))
  def title_display(self) -> str:
    return self.title or C_("song title placeholder", "Unknown")

  @GObject.Property(type=str, default=C_("song artist placeholder", "Unknown"))
  def artist_display(self) -> str:
    return self.artist or C_("song artist placeholder", "Unknown")

  @GObject.Property(type=str, default=C_("song album placeholder", "Unknown"))
  def album_display(self) -> str:
    return self.album or C_("song album placeholder", "Unknown")

  @GObject.Property(type=Gdk.Texture)
  def cover(self) -> Gdk.Texture:
    """Cover of the song"""
    return self._file.get_cover_texture()

  @GObject.Property(type=str)
  def path(self) -> str:
    """Path to the loaded song"""
    return self._file.path

  @property
  def duration(self) -> int:
    """Duration of the song in seconds"""
    return self._file.duration
