from gettext import pgettext as C_
from typing import Union

from gi.repository import Gdk, GObject

from chronograph.internal import Constants, Schema
from chronograph.utils.file_backend import FileManager
from chronograph.utils.file_parsers import parse_files
from chronograph.utils.lyrics import LyricsFile, LyricsFormat
from chronograph.utils.media import FileID3, FileMP4, FileUntaggable, FileVorbis

_title_palceholder = C_("song title placeholder", "Unknown")
_artist_placeholder = C_("song artist placeholder", "Unknown")
_album_placeholder = C_("song album placeholder", "Unknown")


class SongCardModel(GObject.Object):
  __gtype_name__ = "SongCardModel"
  __gsignals__ = {"lyr-format-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,))}

  # Properties without exclicit getters/setters
  path: str = GObject.Property(type=str, default="")
  duration: int = GObject.Property(type=int, default=0, flags=GObject.PARAM_READABLE)
  lyrics_format: str = GObject.Property(
    type=str, default=C_("means lyrics absence", "None")
  )

  def __init__(
    self,
    media_file: Union[FileID3, FileVorbis, FileMP4, FileUntaggable],
    lyrics_file: LyricsFile,
  ) -> None:
    from chronograph.ui.widgets.song_card import SongCard

    self.mfile = media_file
    self.lyrics_file = lyrics_file

    super().__init__(
      title=media_file.title or "",
      title_display=media_file.title or _title_palceholder,
      artist=media_file.artist or "",
      artist_display=media_file.artist or _artist_placeholder,
      album=media_file.album or "",
      album_display=media_file.album or _album_placeholder,
      cover=media_file.get_cover_texture(),
      path=media_file.path,
      duration=media_file.duration,
      lyrics_format=LyricsFormat.translate(lyrics_file.highest_format),
    )

    FileManager().connect("renamed", self._on_any_file_renamed)
    FileManager().connect("deleted", self._on_any_file_deleted)
    self.lyrics_file.connect("notify::highest-format", self._lyrics_fmt_changed)

    self.widget = SongCard(self)

  def save(self) -> None:
    """Save changes to the file"""
    self.mfile.save()

  def _lyrics_fmt_changed(self, lyrics_file: LyricsFile, _pspec) -> None:
    fmt_val: int = lyrics_file.highest_format
    self.set_property("lyrics_format", LyricsFormat.translate(fmt_val))
    self.emit("lyr-format-changed", fmt_val)

  def _on_any_file_renamed(self, _file_manager, new_path: str, old_path: str) -> None:
    if old_path == self.path:
      self.set_property("path", new_path)
      self.mfile = parse_files([new_path])[0]

      # Rename associated lyrics files
      lrc_suffix = Schema.get("root.settings.file-manipulation.format")
      elrc_prefix = Schema.get("root.settings.file-manipulation.elrc-prefix")
      lrc_path = self.lyrics_file.media_bind_path.with_suffix(lrc_suffix)
      elrc_path = self.lyrics_file.media_bind_path.with_name(
        elrc_prefix + self.lyrics_file.media_bind_path.name
      ).with_suffix(lrc_suffix)
      self.lyrics_file.set_property("lrc-path", str(lrc_path))
      self.lyrics_file.set_property("elrc-path", str(elrc_path))

  def _on_any_file_deleted(self, _file_manager, deleted_file: str) -> None:
    if self.path == deleted_file:
      Constants.WIN.library.remove(self.widget)
      Constants.WIN.library_list.remove(self.widget.get_list_mode())

  @GObject.Property(type=str, default="")
  def title(self) -> str:
    """Title of the song"""
    return self.mfile.title or ""

  @title.setter
  def title(self, new_title: str) -> None:
    try:
      self.mfile.set_str_data("TIT2", new_title)
      self.notify("title_display")
    except NotImplementedError:
      pass

  @GObject.Property(type=str, default=_title_palceholder)
  def title_display(self) -> str:
    """Displayable title of the song"""
    return self.mfile.title or _title_palceholder

  @GObject.Property(type=str, default="")
  def artist(self) -> str:
    """Artist of the song"""
    return self.mfile.artist or ""

  @artist.setter
  def artist(self, new_artist: str) -> None:
    try:
      self.mfile.set_str_data("TPE1", new_artist)
      self.notify("artist_display")
    except NotImplementedError:
      pass

  @GObject.Property(type=str, default=_artist_placeholder)
  def artist_display(self) -> str:
    """Displayable artist of the song"""
    return self.mfile.artist or _artist_placeholder

  @GObject.Property(type=str, default="")
  def album(self) -> str:
    """Album of the song"""
    return self.mfile.album or ""

  @album.setter
  def album(self, new_album: str) -> None:
    try:
      self.mfile.set_str_data("TALB", new_album)
      self.notify("album_display")
    except NotImplementedError:
      pass

  @GObject.Property(type=str, default=_album_placeholder)
  def album_display(self) -> str:
    """Displayable album of the song"""
    return self.mfile.album or _album_placeholder

  @GObject.Property(type=Gdk.Texture, default=Constants.COVER_PLACEHOLDER)
  def cover(self) -> Gdk.Texture:
    """Cover of the song"""
    return self.mfile.get_cover_texture()
