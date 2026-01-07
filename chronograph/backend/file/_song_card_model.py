from gettext import pgettext as C_
from pathlib import Path

from gi.repository import Gdk, GObject, Gtk

from chronograph.backend.file import AvailableLyrics
from chronograph.backend.file_parsers import parse_file
from chronograph.backend.media.file import BaseFile
from chronograph.internal import Constants

_title_palceholder = C_("song title placeholder", "Unknown")
_artist_placeholder = C_("song artist placeholder", "Unknown")
_album_placeholder = C_("song album placeholder", "Unknown")


class SongCardModel(GObject.Object):
  __gtype_name__ = "SongCardModel"

  duration: int = GObject.Property(type=int, default=0)
  available_lyrics: AvailableLyrics = GObject.Property(
    type=AvailableLyrics, default=AvailableLyrics.NONE
  )
  tags: Gtk.StringList = GObject.Property(
    type=Gtk.StringList, default=Gtk.StringList.new()
  )

  def __init__(self, mediafile: Path, uuid: str, **kwargs) -> None:
    self.mediafile = mediafile
    self.uuid = uuid
    media = parse_file(mediafile)
    if media is None:
      raise ValueError(f"Unsupported media file: {mediafile}")
    super().__init__(duration=media.duration, **kwargs)
    self._title = media.title or ""
    self._artist = media.artist or ""
    self._album = media.album or ""

  def media(self) -> BaseFile:
    """Opens a new connection to a mediafile.

    Please, do not store references to result of this function if you're not forced to.

    Returns
    -------
    BaseFile
      A fresh instance of `BaseFile` depending on mutagen realization
    """
    return parse_file(self.mediafile)

  @GObject.Property(type=str, default="")
  def title(self) -> str:
    return self._title

  @title.setter
  def title(self, title: str) -> None:
    self.media().set_str_data("TIT2", title).save()
    self._title = title
    self.notify("title_display")

  @GObject.Property(type=str, default=_title_palceholder)
  def title_display(self) -> str:
    return self.title or _title_palceholder

  @GObject.Property(type=str, default="")
  def artist(self) -> str:
    return self._artist

  @artist.setter
  def artist(self, artist: str) -> None:
    self.media().set_str_data("TPE1", artist).save()
    self._artist = artist
    self.notify("artist_display")

  @GObject.Property(type=str, default=_artist_placeholder)
  def artist_display(self) -> str:
    return self.artist or _artist_placeholder

  @GObject.Property(type=str, default="")
  def album(self) -> str:
    return self._album

  @album.setter
  def album(self, album: str) -> None:
    self.media().set_str_data("TALB", album).save()
    self._album = album
    self.notify("album_display")

  @GObject.Property(type=str, default=_album_placeholder)
  def album_display(self) -> str:
    return self.album or _album_placeholder

  @GObject.Property(type=Gdk.Texture)
  def cover(self) -> Gdk.Texture:
    if (tx := self.media().get_cover_texture()) is not None:
      return tx
    return Constants.COVER_PLACEHOLDER
