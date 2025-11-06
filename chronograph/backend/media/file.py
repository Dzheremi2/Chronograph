import contextlib
from typing import Literal, Optional

import mutagen
from gi.repository import Gdk, GdkPixbuf, GObject

from chronograph.backend.lyrics.lyrics import Lyrics
from chronograph.internal import Constants


class BaseFile(GObject.Object):
  __gtype_name__ = "BaseFile"

  path: str = GObject.Property(type=str, default="")
  title: str = GObject.Property(type=str, default="")
  artist: str = GObject.Property(type=str, default="")
  album: str = GObject.Property(type=str, default="")
  duration: int = GObject.Property(type=str, default=0)

  def __init__(self, path: str) -> None:
    super().__init__()
    self._cover_bytes: Optional[bytes] = None
    self._mutagen_file: mutagen.FileType = None
    self._cover_updated: bool = False
    self.props.path = path
    self._load_from_file(path)

  def save(self) -> None:
    """Saves the changes to the file"""
    self._mutagen_file.save()

  def _load_from_file(self, path: str) -> None:
    self._mutagen_file = mutagen.File(path)
    with contextlib.suppress(Exception):
      self.props.duration = self._mutagen_file.info.length

  @GObject.Property(type=Gdk.Texture)
  def cover_texture(self) -> Gdk.Texture:
    """Cover of the track"""
    if self._cover_bytes:
      loader = GdkPixbuf.PixbufLoader.new()
      loader.write(self._cover_bytes)
      loader.close()
      pixbuf = loader.get_pixbuf()

      scaled_pixbuf = pixbuf.scale_simple(160, 160, GdkPixbuf.InterpType.BILINEAR)
      return Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
    return Constants.COVER_PLACEHOLDER

  @property
  def cover_bytes(self) -> Optional[bytes]:
    """Cover image bytes, `None` for no cover (placeholder used)"""
    return self._cover_bytes

  @cover_bytes.setter
  def cover_bytes(self, new_bytes: Optional[bytes]) -> None:
    self._cover_bytes = new_bytes
    self.notify("cover_texture")

  def _compress_images(self) -> None:
    """Makes the loaded MutagenFile instance to have compressed covers without saving to the file

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def _load_tags(self) -> None:
    """Reads the string data from file and binds it to the instance

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def _load_cover(self) -> None:
    """Reads the cover from the file and binds it to the instance

    Should be implemented in file specific child classes
    """
    raise NotImplementedError

  def set_tag(
    self, tag_name: Literal["TITLE", "ARTIST", "ALBUM"], new_val: str
  ) -> None:
    """Sets the provided tag in ID3 format to the provided value

    Parameters
    ----------
    tag_name : Literal["TITLE", "ARTIST", "ALBUM"]
      Wide-known tag name
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
    self._compress_images()
    self._load_cover()
    self._load_tags()


class Tag:
  @staticmethod
  def determine(  # noqa: PLR0911
    media_type: Literal["ID3", "VORBIS", "MP4"],
    tag: Literal["TITLE", "ARTIST", "ALBUM"],
  ) -> str:
    """Gives a correct tag name for specified media container type by tag wide-known name

    Parameters
    ----------
    media_type : Literal['ID3', 'VORBIS', 'MP4']
      Media file container type
    tag : Literal['TITLE', 'ARTIST', 'ALBUM']
      Tag wide-known name

    Returns
    -------
    str
        Tag used by container tag system
    """
    # fmt: off
    match media_type:
      case "ID3":
        match tag:
          case "TITLE": return "TIT2"
          case "ARTIST": return "TPE1"
          case "ALBUM": return "TALB"
      case "MP4":
        match tag:
          case "TITLE": return "\xa9nam"
          case "ARTIST": return "\xa9ART"
          case "ALBUM": return "\xa9alb"
      case "VORBIS":
        match tag:
          case "TITLE": return "title"
          case "ARTIST": return "artist"
          case "ALBUM": return "album"
    # fmt: on
