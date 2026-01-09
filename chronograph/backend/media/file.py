import contextlib
import sys
import time
from pathlib import Path
from typing import Optional, Self

import mutagen
from gi.repository import Gdk, GdkPixbuf, GLib

from chronograph.backend.lyrics.interfaces import LyricsBase
from dgutils.decorators import baseclass


@baseclass
class BaseFile:
  """A base class for mutagen filetypes classes

  Parameters
  ----------
  path : str
      A path to file for loading

  Props
  --------
  ::

      title : str -> Title of the song
      artist : str -> Artist of the song
      album : str -> Album of the song
      cover : Gdk.Texture | str -> Cover of the song
      path : str -> Path to the loaded song
      duration : int -> Duration of the loaded song
  """

  __gtype_name__ = "BaseFile"

  _title: str = None
  _artist: str = None
  _album: str = None
  _cover: Optional[bytes] = None
  _mutagen_file: mutagen.FileType = None
  _duration: float = None
  _cover_updated: bool = False

  def __init__(self, path: str) -> None:
    self._path: str = path
    self.load_from_file(path)

  def save(self) -> Self:
    """Saves the changes to the file"""
    try:
      self._mutagen_file.save()
      return self
    except (PermissionError, OSError) as exc:
      if sys.platform != "win32":
        raise

      try:
        from gi.repository import Gst

        from chronograph.backend.player import Player
      except Exception:
        raise exc from exc

      player = Player()
      current_uri = player._gst_player.props.uri  # noqa: SLF001
      target_uri = Path(self._path).absolute().as_uri()
      if current_uri != target_uri:
        raise exc from exc

      was_playing = player.playing
      pos_ns = player._gst_player.props.position  # noqa: SLF001
      player.stop()
      time.sleep(0.05)

      try:
        self._mutagen_file.save()
      finally:
        player.set_file(Path(self._path))
        if pos_ns > 0:
          player.seek(int(pos_ns / Gst.MSECOND))
        if was_playing:
          player.set_property("playing", True)
          player.play_pause()

    return self

  def load_from_file(self, path: str) -> None:
    """Generates mutagen file instance for path

    Parameters
    ----------
    path : str
      /path/to/file
    """
    self._mutagen_file = mutagen.File(path)
    with contextlib.suppress(Exception):
      self._duration = self._mutagen_file.info.length

  def get_cover_texture(self) -> Optional[Gdk.Texture]:
    """Prepares a Gdk.Texture for setting to SongCard.paintable

    Returns
    -------
    Optional[Gdk.Texture]
      `Gdk.Texture` or `None` if no cover is set
    """
    if self._cover:
      loader = GdkPixbuf.PixbufLoader.new()
      loader.write_bytes(GLib.Bytes.new(self._cover))
      loader.close()
      pixbuf = loader.get_pixbuf()

      scaled_pixbuf = pixbuf.scale_simple(160, 160, GdkPixbuf.InterpType.BILINEAR)
      return Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
    return None

  @property
  def title(self) -> str:
    """The title of the song"""
    return self._title

  @title.setter
  def title(self, value: str) -> None:
    self._title = value

  @property
  def artist(self) -> str:
    """The artist of the song"""
    return self._artist

  @artist.setter
  def artist(self, value: str) -> None:
    self._artist = value

  @property
  def album(self) -> str:
    """The album of the song"""
    return self._album

  @album.setter
  def album(self, value: str) -> None:
    self._album = value

  @property
  def cover(self) -> bytes:
    """The cover of the song"""
    return self._cover

  @cover.setter
  def cover(self, data: bytes) -> None:
    self._cover = data

  @property
  def path(self) -> str:
    """Path to the media file"""
    return self._path

  @property
  def duration(self) -> int:
    """Duration of the song"""
    return round(self._duration)

  @property
  def duration_ns(self) -> int:
    """Duration of the song in nanoseconds"""
    return int(self._duration * 1_000_000_000) if self._duration else 0

  def load_str_data(self) -> None:
    """Reads the string data from file and binds it to the instance

    Should be implemented in file specific child classes
    """
    raise NotImplementedError(self.path)

  def load_cover(self) -> None:
    """Reads the cover from the file and binds it to the instance

    Should be implemented in file specific child classes
    """
    raise NotImplementedError(self.path)

  def set_str_data(self, tag_name: str, new_val: str) -> Self:
    """Sets the provided tag in ID3 format to the provided value

    Parameters
    ----------
    tag_name : str
        ID3 tag (must work in all realizations using TAGS_CONJUNCTION)
    new_val : str
        value to be set

    Should be implemented in file specific child classes
    """
    raise NotImplementedError(self.path)

  def set_cover(self, img_path: Optional[str]) -> Self:
    """Sets the cover of the instance to a provided image

    Parameters
    ----------
    img_path : Optional[str]
        /path/to/an/image

    Should be implemented in file specific child classes
    """
    raise NotImplementedError(self.path)

  def embed_lyrics(self, lyrics: Optional[LyricsBase], *, force: bool = False) -> Self:
    """Embeds the lyrics to the corresponding tags in realization

    Parameters
    ----------
    lyrics : Optional[StartLyrics]
        lyrics, if `None` lyrics removed
    force : bool, by default `False`
        Allows to embed lyrics independently of schema settings

    Should be implemented in file specific child classes
    """
    raise NotImplementedError(self.path)


class TaggableFile(BaseFile):
  """Base class for files that support metadata editing.

  Parameters
  ----------
  path : str
      A path to file for loading
  """

  __gtype_name__ = "TaggableFile"

  def __init__(self, path: str) -> None:
    super().__init__(path)
    self.load_cover()
    self.load_str_data()
