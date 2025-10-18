from gettext import pgettext as C_
from typing import Union

from gi.repository import Gdk, GObject

from chronograph.utils.lyrics import LyricsFile, LyricsFormat
from chronograph.utils.media import FileID3, FileMP4, FileUntaggable, FileVorbis

_title_palceholder = C_("song title placeholder", "Unknown")
_artist_placeholder = C_("song artist placeholder", "Unknown")
_album_placeholder = C_("song album placeholder", "Unknown")


class SongCardModel(GObject.Object):
  __gtype_name__ = "SongCardModel"
  __gsignals__ = {"lyr-format-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,))}

  title: str = GObject.Property(type=str, default="")
  title_display: str = GObject.Property(type=str, default=_title_palceholder)
  artist: str = GObject.Property(type=str, default="")
  artist_display: str = GObject.Property(type=str, default=_artist_placeholder)
  album: str = GObject.Property(type=str, default="")
  album_display: str = GObject.Property(type=str, default=_album_placeholder)
  cover: Gdk.Texture = GObject.Property(type=Gdk.Texture)
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

    self.lyrics_file.connect("notify::highest-format", self._lyrics_fmt_changed)

    self.widget = SongCard(self)

  def save(self) -> None:
    """Save changes to the file"""
    self.mfile.save()

  def _lyrics_fmt_changed(self, lyrics_file: LyricsFile, _pspec) -> None:
    fmt_val: int = lyrics_file.highest_format
    self.set_property("lyrics_format", LyricsFormat.translate(fmt_val))
    self.emit("lyr-format-changed", fmt_val)
