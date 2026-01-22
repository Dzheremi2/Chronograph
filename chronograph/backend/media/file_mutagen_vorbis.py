import base64
import contextlib
from pathlib import Path
from typing import Optional, Self

import magic
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
from chronograph.internal import Schema

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

  def load_str_data(self, tags: list = ("title", "artist", "album")) -> None:
    if self._mutagen_file.tags is not None:
      for tag in tags:
        try:
          text = (
            "Unknown"
            if not self._mutagen_file.tags[tag.lower()][0]
            else self._mutagen_file.tags[tag.lower()][0]
          )
          setattr(self, f"_{tag}", text)
        except KeyError:
          try:
            text = (
              "Unknown"
              if not self._mutagen_file.tags[tag.upper()][0]
              else self._mutagen_file.tags[tag.upper()][0]
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
    if tags_conjunction[tag_name][1].upper() in self._mutagen_file.tags:
      self._mutagen_file.tags[tags_conjunction[tag_name][1].upper()] = new_val
    else:
      self._mutagen_file.tags[tags_conjunction[tag_name][1]] = new_val
    setattr(self, tags_conjunction[tag_name][0], new_val)
    return self

  def embed_lyrics(
    self, lyrics: Optional[ChronieLyrics], *, force: bool = False
  ) -> Self:
    if not force:
      return self
    if lyrics is not None:
      target = Schema.get(
        "root.settings.do-lyrics-db-updates.embed-lyrics.default"
      ).lower()
      chosen = choose_export_format(lyrics, target)
      if chosen is None:
        return self
      try:
        text = export_chronie(lyrics, chosen)
      except LyricsConversionError:
        text = export_chronie(lyrics, "plain")
      if not Schema.get("root.settings.do-lyrics-db-updates.embed-lyrics.vorbis"):
        self._mutagen_file.tags["UNSYNCEDLYRICS"] = text
      else:
        self._mutagen_file.tags["UNSYNCEDLYRICS"] = export_chronie(lyrics, "plain")
        self._mutagen_file.tags["LYRICS"] = text
      self.save()
      return self

    with contextlib.suppress(KeyError):
      del self._mutagen_file.tags["UNSYNCEDLYRICS"]

    with contextlib.suppress(KeyError):
      del self._mutagen_file.tags["LYRICS"]

    self.save()
    return self

  def read_lyrics(self) -> Optional[ChronieLyrics]:
    tags = self._mutagen_file.tags
    use_vorbis = Schema.get("root.settings.do-lyrics-db-updates.embed-lyrics.vorbis")

    if use_vorbis:
      lyrics: str = tags.get("LYRICS", "").strip()
      if not lyrics:
        lyrics: str = tags.get("UNSYNCEDLYRICS", "").strip()
      if lyrics:
        return chronie_from_text(lyrics)
      return None

    lyrics: str = tags.get("UNSYNCEDLYRICS", "").strip()
    return chronie_from_text(lyrics) if lyrics else None
