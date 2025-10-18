import io
from typing import Optional

from mutagen.mp4 import MP4Cover
from PIL import Image

from chronograph.internal import Schema
from chronograph.utils.lyrics import Lyrics, LyricsFormat

from .file import TaggableFile

tags_conjunction = {
  "TIT2": ["_title", "\xa9nam"],
  "TPE1": ["_artist", "\xa9ART"],
  "TALB": ["_album", "\xa9alb"],
}


# pylint: disable=attribute-defined-outside-init
class FileMP4(TaggableFile):
  """A MPEG-4 compatible file class. Inherited from `TaggableFile`

  Parameters
  ----------
  path : str
      A path to the file for loading
  """

  __gtype_name__ = "FileMP4"

  def compress_images(self) -> None:
    if Schema.get("root.settings.general.compressed-covers.enabled"):
      quality = Schema.get("root.settings.general.compressed-covers.level")
      tags = self._mutagen_file.tags
      if tags is None or "covr" not in tags:
        return

      bytes_origin = tags["covr"][0]

      with Image.open(io.BytesIO(bytes_origin)) as img:
        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        bytes_compressed = buffer.getvalue()

      tags["covr"][0] = MP4Cover(bytes_compressed, imageformat=MP4Cover.FORMAT_JPEG)
      self.cover = tags["covr"][0]

  def load_cover(self) -> None:
    """Extracts cover from song file. If no cover, then sets cover as `icon`"""
    if (
      "covr" not in self._mutagen_file.tags
      or not self._mutagen_file.tags["covr"]
      or self._mutagen_file.tags is None
    ):
      self.cover = None
    else:
      picture = self._mutagen_file.tags["covr"][0]
      if picture != "EMPTY_COVER":
        self.cover = picture

  def load_str_data(self) -> None:
    """Sets all string data from tags. If data is unavailable, then sets `Unknown`"""
    if self._mutagen_file.tags is not None:
      try:
        if (_title := self._mutagen_file.tags["\xa9nam"]) is not None:
          self.title = _title[0]
      except KeyError:
        pass

      try:
        if (_artist := self._mutagen_file.tags["\xa9ART"]) is not None:
          self.artist = _artist[0]
      except KeyError:
        pass

      try:
        if (_album := self._mutagen_file.tags["\xa9alb"]) is not None:
          self.album = _album[0]
      except KeyError:
        pass

  def set_cover(self, img_path: Optional[str]) -> None:
    """Sets `self._mutagen_file` cover to specified image or removing it if image specified as `None`

    Parameters
    ----------
    img_path : str | None
        path to image or None if cover should be deleted
    """
    if img_path is not None:
      cover_bytes = open(img_path, "rb").read()  # noqa: SIM115
      if self._mutagen_file.tags:
        cover_val = []
        if "covr" in self._mutagen_file.tags:
          cover_val = self._mutagen_file.tags["covr"]

        try:
          cover_val[0] = MP4Cover(cover_bytes, MP4Cover.FORMAT_PNG)
        except IndexError:
          cover_val.append(MP4Cover(cover_bytes, MP4Cover.FORMAT_PNG))

        self._mutagen_file.tags["covr"] = cover_val
        self.cover = cover_val[0]
    else:
      if self._mutagen_file.tags:
        if "covr" in self._mutagen_file.tags:
          del self._mutagen_file.tags["covr"]
        else:
          self._mutagen_file.add_tags()
      self.cover = None

  def set_str_data(self, tag_name: str, new_val: str) -> None:  # noqa: D417
    r"""Sets string tags to provided value

    Parameters
    ----------
    tag_name : str

    ::

        "TIT2" -> [_title, "\xa9nam"]
        "TPE1" -> [_artist, "\xa9ART"]
        "TALB" -> [_album, "\xa9alb"]

    new_val : str
        new value for setting
    """
    if self._mutagen_file.tags is None:
      self._mutagen_file.add_tags()

    self._mutagen_file.tags[tags_conjunction[tag_name][1]] = new_val
    setattr(self, tags_conjunction[tag_name][0], new_val)

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> None:
    if lyrics is not None:
      if Schema.get("root.settings.file-manipulation.embed-lyrics.enabled") or force:
        if self._mutagen_file.tags is None:
          self._mutagen_file.add_tags()

        target_format = LyricsFormat[
          Schema.get("root.settings.file-manipulation.embed-lyrics.default").upper()
        ]
        target_format = LyricsFormat.from_int(
          min(target_format.value, lyrics.format.value)
        )
        text = lyrics.of_format(target_format)

        self._mutagen_file.tags["\xa9lyr"] = text
        self.save()
      return

    try:
      if self._mutagen_file.tags is not None:
        del self._mutagen_file.tags["\xa9lyr"]
    except KeyError:
      pass

    self.save()
