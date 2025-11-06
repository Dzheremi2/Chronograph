import contextlib
import io
from typing import Optional

from mutagen.mp4 import MP4Cover
from PIL import Image

from chronograph.backend.lyrics import Lyrics, LyricsFormat
from chronograph.internal import Schema

from .file import Tag, TaggableFile


class FileMP4(TaggableFile):
  __gtype_name__ = "FileMP4"

  def _compress_images(self) -> None:
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
      self.cover_bytes = tags["covr"][0]

  def _load_cover(self) -> None:
    if (
      "covr" not in self._mutagen_file.tags
      or not self._mutagen_file.tags["covr"]
      or self._mutagen_file.tags is None
    ):
      self.cover_bytes = None
    else:
      picture = self._mutagen_file.tags["covr"][0]
      if picture != "EMPTY_COVER":
        self.cover_bytes = picture

  def _load_tags(self) -> None:
    if self._mutagen_file.tags is not None:
      with contextlib.suppress(KeyError):
        if (_title := self._mutagen_file.tags["\xa9nam"]) is not None:
          self.props.title = _title[0]

      with contextlib.suppress(KeyError):
        if (_artist := self._mutagen_file.tags["\xa9ART"]) is not None:
          self.props.artist = _artist[0]

      with contextlib.suppress(KeyError):
        if (_album := self._mutagen_file.tags["\xa9alb"]) is not None:
          self.props.album = _album[0]

  def set_cover(self, img_path: Optional[str]) -> None:  # noqa: D102
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
        self.cover_bytes = cover_val[0]
    else:
      if self._mutagen_file.tags:
        if "covr" in self._mutagen_file.tags:
          del self._mutagen_file.tags["covr"]
        else:
          self._mutagen_file.add_tags()
      self.cover_bytes = None

  def set_tag(self, tag_name: str, new_val: str) -> None:  # noqa: D102
    _tag_name = Tag.determine("MP4", tag_name)
    if self._mutagen_file.tags is None:
      self._mutagen_file.add_tags()

    self._mutagen_file.tags[_tag_name] = new_val
    self.set_property(tag_name.lower(), new_val)

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> None:  # noqa: D102
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

    with contextlib.suppress(KeyError):
      if self._mutagen_file.tags is not None:
        del self._mutagen_file.tags["\xa9lyr"]

    self.save()
