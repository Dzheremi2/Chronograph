import base64
import contextlib
import io
from pathlib import Path
from typing import Literal, Optional, Union

import magic
from mutagen.flac import FLAC, Picture
from mutagen.flac import error as FLACError
from PIL import Image

from chronograph.backend.lyrics import Lyrics, LyricsFormat
from chronograph.internal import Schema

from .file import Tag, TaggableFile


class FileVorbis(TaggableFile):
  __gtype_name__ = "FileVorbis"

  def _compress_images(self) -> None:
    if Schema.get("root.settings.general.compressed-covers.enabled"):
      quality = Schema.get("root.settings.general.compressed-covers.level")
      pic: Union[Picture, None] = None

      if isinstance(self._mutagen_file, FLAC) and self._mutagen_file.pictures:
        pic = self._mutagen_file.pictures[0]
      else:
        encoded_blocks = self._mutagen_file.get("metadata_block_picture", [])
        for base64_data in encoded_blocks:
          try:
            pic = Picture(base64.b64decode(base64_data))
            break
          except FLACError:
            continue

      if not pic or not pic.data:
        return

      with Image.open(io.BytesIO(pic.data)) as img:
        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        bytes_compressed = buffer.getvalue()

      pic.data = bytes_compressed
      pic.mime = "image/jpeg"

      if isinstance(self._mutagen_file, FLAC):
        self._mutagen_file.clear_pictures()
        self._mutagen_file.add_picture(pic)

      picture_data = pic.write()
      encoded = base64.b64encode(picture_data).decode("ascii")
      self._mutagen_file["metadata_block_picture"] = [encoded]

      self.cover_bytes = bytes_compressed

  def _load_cover(self) -> None:
    if isinstance(self._mutagen_file, FLAC) and self._mutagen_file.pictures:
      if self._mutagen_file.pictures[0].data is not None:
        self.cover_bytes = self._mutagen_file.pictures[0].data
      else:
        self.cover_bytes = None
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
        self.cover_bytes = None
      else:
        self.cover_bytes = _data
    else:
      self.cover_bytes = None

  def _load_tags(self) -> None:
    tags = ["title", "artist", "album"]
    if self._mutagen_file.tags is not None:
      for tag in tags:
        try:
          text = (
            None
            if not self._mutagen_file.tags[tag.lower()][0]
            else self._mutagen_file.tags[tag.lower()][0]
          )
          self.set_property(tag, text)
        except KeyError:
          try:
            text = (
              None
              if not self._mutagen_file.tags[tag.upper()][0]
              else self._mutagen_file.tags[tag.upper()][0]
            )
            self.set_property(tag, text)
          except KeyError:
            self.set_property(tag, None)
    if self.props.title is None:
      self.props.title = Path(self._path).name

  def set_cover(self, img_path: Optional[str]) -> None:  # noqa: D102
    if img_path is not None:
      if isinstance(self._mutagen_file, FLAC):
        self._mutagen_file.clear_pictures()

      if "metadata_block_picture" in self._mutagen_file:
        self._mutagen_file["metadata_block_picture"] = []

      self.cover_bytes = data = open(img_path, "rb").read()  # noqa: SIM115

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
        self.cover_bytes = None

      if "metadata_block_picture" in self._mutagen_file:
        self._mutagen_file["metadata_block_picture"] = []
        self.cover_bytes = None

  def set_tag(  # noqa: D102
    self, tag_name: Literal["TITLE", "ARTIST", "ALBUM"], new_val: str
  ) -> None:
    _tag_name = Tag.determine("VORBIS", tag_name)
    if _tag_name.upper() in self._mutagen_file.tags:
      self._mutagen_file.tags[_tag_name.upper()] = new_val
    else:
      self._mutagen_file.tags[_tag_name] = new_val
    self.set_property(tag_name.lower(), new_val)

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> None:  # noqa: D102
    if lyrics is not None:
      if Schema.get("root.settings.file-manipulation.embed-lyrics.enabled") or force:
        target_format = LyricsFormat[
          Schema.get("root.settings.file-manipulation.embed-lyrics.default").upper()
        ]
        target_format = LyricsFormat.from_int(
          min(target_format.value, lyrics.format.value)
        )
        text = lyrics.of_format(target_format)
        if not Schema.get("root.settings.file-manipulation.embed-lyrics.vorbis"):
          self._mutagen_file.tags["UNSYNCEDLYRICS"] = text
        else:
          self._mutagen_file.tags["UNSYNCEDLYRICS"] = lyrics.of_format(
            LyricsFormat.PLAIN
          )

          self._mutagen_file.tags["LYRICS"] = text
        self.save()
      return

    with contextlib.suppress(KeyError):
      del self._mutagen_file.tags["UNSYNCEDLYRICS"]

    with contextlib.suppress(KeyError):
      del self._mutagen_file.tags["LYRICS"]

    self.save()
