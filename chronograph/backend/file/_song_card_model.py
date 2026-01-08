from datetime import datetime
from gettext import pgettext as C_
from pathlib import Path

from gi.repository import Gdk, GObject, Gtk

from chronograph.backend.db.models import Track
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

  def __init__(self, mediafile: Path, uuid: str, **kwargs) -> None:
    self.mediafile: Path = mediafile
    self.uuid: str = uuid
    self._tags = list(Track.get_by_id(self.uuid).tags_json or [])
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

  @GObject.Property(type=str)
  def imported_at(self) -> str:
    value: int = Track.get_by_id(self.uuid).imported_at
    return datetime.fromtimestamp(float(value)).strftime("%d.%m.%Y, %H:%M.%S")  # noqa: DTZ006

  @GObject.Property(type=str, default="---")
  def last_modified(self) -> str:
    value = Track.get_by_id(self.uuid).latest_lyric_update
    return (
      datetime.fromtimestamp(float(value)).strftime("%d.%m.%Y, %H:%M.%S")  # noqa: DTZ006
      if value is not None
      else "---"
    )

  @GObject.Property(type=object)
  def tags(self) -> list[str]:
    return list(self._tags)

  @tags.setter
  def tags(self, tags: list[str]) -> None:
    tags = list(tags or [])
    if tags == self._tags:
      return
    Track.update(tags_json=tags).where(Track.track_uuid == self.uuid).execute()
    self._tags = tags
    self.notify("tags")
