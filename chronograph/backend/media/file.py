import contextlib
from typing import Optional

import mutagen
from gi.repository import Gdk, GdkPixbuf

from chronograph.backend.lyrics import Lyrics
from chronograph.internal import Constants
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

  def save(self) -> None:
    """Saves the changes to the file"""
    self._mutagen_file.save()

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

  def get_cover_texture(self) -> Gdk.Texture:
    """Prepares a Gdk.Texture for setting to SongCard.paintable

    Returns
    -------
    Gdk.Texture
        Gdk.Texture or a placeholder texture if no cover is set
    """
    if self._cover:
      loader = GdkPixbuf.PixbufLoader.new()
      loader.write(self._cover)
      loader.close()
      pixbuf = loader.get_pixbuf()

      scaled_pixbuf = pixbuf.scale_simple(160, 160, GdkPixbuf.InterpType.BILINEAR)
      return Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
    return Constants.COVER_PLACEHOLDER

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

  def compress_images(self) -> None:
    """Makes the loaded MutagenFile instance to have compressed covers without saving to the file

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def load_str_data(self) -> None:
    """Reads the string data from file and binds it to the instance

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def load_cover(self) -> None:
    """Reads the cover from the file and binds it to the instance

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def set_str_data(self, tag_name: str, new_val: str) -> None:
    """Sets the provided tag in ID3 format to the provided value

    Parameters
    ----------
    tag_name : str
        ID3 tag (must work in all realizations using TAGS_CONJUNCTION)
    new_val : str
        value to be set

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def set_cover(self, img_path: Optional[str]) -> None:
    """Sets the cover of the instance to a provided image

    Parameters
    ----------
    img_path : Optional[str]
        /path/to/an/image

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> None:
    """Embeds the lyrics to the corresponding tags in realization

    Parameters
    ----------
    lyrics : Optional[str]
        lyrics, if `None` lyrics removed
    force : bool, by default `False`
        Allows to embed lyrics independently of schema settings

    Should be implemented in file specific child classes
    """
    raise NotImplementedError


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
    self.compress_images()
    self.load_cover()
    self.load_str_data()
