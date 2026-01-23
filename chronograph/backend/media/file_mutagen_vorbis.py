import base64
import contextlib
from pathlib import Path
from typing import Optional, Self

import magic
from mutagen._vorbis import VCommentDict
from mutagen.flac import FLAC, Picture
from mutagen.flac import error as FLACError
from PIL import Image

from chronograph.backend.lyrics import (
  ChronieLyrics,
  LyricsConversionError,
  choose_export_format,
  export_chronie,
)
from chronograph.backend.lyrics.formats import chronie_from_text

from .file import TaggableFile

tags_conjunction = {
  "TIT2": ["_title", "title"],
  "TPE1": ["_artist", "artist"],
  "TALB": ["_album", "album"],
}


class FileVorbis(TaggableFile):
  """A Vorbis (ogg, flac) compatible file class. Inherited from `TaggableFile`

  Parameters
  ----------
  path : str
    A path to file for loading
  """

  __gtype_name__ = "FileVorbis"

  @property
  def tags(self) -> VCommentDict:
    return self._mutagen_file.tags  # ty:ignore[invalid-return-type]

  def load_cover(self) -> None:
    if isinstance(self._mutagen_file, FLAC) and self._mutagen_file.pictures:
      if self._mutagen_file.pictures[0].data is not None:
        self._cover = self._mutagen_file.pictures[0].data
      else:
        self._cover = None
    elif self._mutagen_file.get("metadata_block_picture", []):
      _data = None
      for base64_data in self._mutagen_file.get("metadata_block_picture", []):
        try:
          _data = base64.b64decode(base64_data)
        except (TypeError, ValueError):
          continue

        try:
          _data = Picture(_data).data
        except FLACError:
          continue

      if _data is None:
        self._cover = None
      else:
        self._cover = _data
    else:
      self._cover = None

  def load_str_data(self) -> None:
    tags = ("title", "artist", "album")
    if self.tags is not None:
      for tag in tags:
        try:
          text = (
            "Unknown"
            if not self.tags[tag.lower()][0]
            else self.tags[tag.lower()][0]
          )
          setattr(self, f"_{tag}", text)
        except KeyError:
          try:
            text = (
              "Unknown"
              if not self.tags[tag.upper()][0]
              else self.tags[tag.upper()][0]
            )
            setattr(self, f"_{tag}", text)
          except KeyError:
            setattr(self, f"_{tag}", "Unknown")
    if self._title == "Unknown":
      self._title = Path(self._path).name

  def set_cover(self, img_path: Optional[str]) -> Self:
    if img_path is not None:
      if isinstance(self._mutagen_file, FLAC):
        self._mutagen_file.clear_pictures()

      if "metadata_block_picture" in self._mutagen_file:
        self._mutagen_file["metadata_block_picture"] = []

      self._cover = data = open(img_path, "rb").read()  # noqa: SIM115

      picture = Picture()
      picture.data = data
      picture.mime = magic.from_file(img_path, mime=True)
      img = Image.open(img_path)
      picture.width = img.width
      picture.height = img.height

      if isinstance(self._mutagen_file, FLAC):
        self._mutagen_file.add_picture(picture)

      picture_data = picture.write()
      encoded_data = base64.b64encode(picture_data)
      vcomment_value = encoded_data.decode("ascii")
      if "metadata_block_picture" in self._mutagen_file:
        self._mutagen_file["metadata_block_picture"] = [
          vcomment_value
        ] + self._mutagen_file["metadata_block_picture"]
      else:
        self._mutagen_file["metadata_block_picture"] = [vcomment_value]

    else:
      if isinstance(self._mutagen_file, FLAC):
        self._mutagen_file.clear_pictures()
        self._cover = None

      if "metadata_block_picture" in self._mutagen_file:
        self._mutagen_file["metadata_block_picture"] = []
        self._cover = None
    return self

  def set_str_data(self, tag_name: str, new_val: str) -> Self:
    if tags_conjunction[tag_name][1].upper() in self.tags:
      self.tags[tags_conjunction[tag_name][1].upper()] = new_val
    else:
      self.tags[tags_conjunction[tag_name][1]] = new_val
    setattr(self, tags_conjunction[tag_name][0], new_val)
    return self

  def embed_lyrics(self, lyrics: Optional[ChronieLyrics], target: str) -> Self:
    if lyrics is not None:
      # fmt: off
      match target.lower():
        case "plain": chosen = choose_export_format(lyrics, "plain")
        case "lrc": chosen = choose_export_format(lyrics, "lrc")
        case "elrc": chosen = choose_export_format(lyrics, "enhanced")
        case __: chosen = choose_export_format(lyrics, "plain")
      # fmt: on
      if chosen is None:
        return self
      try:
        text = export_chronie(lyrics, chosen)
      except LyricsConversionError:
        text = export_chronie(lyrics, "plain")
      self.tags["UNSYNCEDLYRICS"] = export_chronie(lyrics, "plain")
      self.tags["LYRICS"] = text
      self.save()
      return self

    with contextlib.suppress(KeyError):
      del self.tags["UNSYNCEDLYRICS"]

    with contextlib.suppress(KeyError):
      del self.tags["LYRICS"]

    self.save()
    return self

  def read_lyrics(self) -> Optional[ChronieLyrics]:
    tags = self.tags

    lyrics: str = tags.get("LYRICS", "").strip()
    if not lyrics:
      lyrics: str = tags.get("UNSYNCEDLYRICS", "").strip()
    if lyrics:
      return chronie_from_text(lyrics)
    return None
