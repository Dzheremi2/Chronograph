import contextlib
import io
from typing import Literal, Optional

from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, USLT
from PIL import Image

from chronograph.backend.lyrics import Lyrics, LyricsFormat
from chronograph.internal import Schema

from .file import Tag, TaggableFile


class FileID3(TaggableFile):
  __gtype_name__ = "FileID3"

  def _compress_images(self) -> None:
    if Schema.get("root.settings.general.compressed-covers.enabled"):
      quality = Schema.get("root.settings.general.compressed-covers.level")
      tags = self._mutagen_file.tags
      if not isinstance(tags, ID3):
        return
      apics = [key for key in tags if key.startswith("APIC")]
      for key in apics:
        apic = tags[key]
        bytes_origin = apic.data

        with Image.open(io.BytesIO(bytes_origin)) as img:
          buffer = io.BytesIO()
          img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
          bytes_compressed = buffer.getvalue()

        apic_compressed = APIC(
          mime="image/jpeg",
          encoding=apic.encoding,
          type=apic.type,
          desc=apic.desc,
          data=bytes_compressed,
        )
        tags[key] = apic_compressed

  def _load_cover(self) -> None:
    if self._mutagen_file.tags is not None:
      pictures = self._mutagen_file.tags.getall("APIC")
      if len(pictures) != 0:
        self.cover_bytes = pictures[0].data
      if len(pictures) == 0:
        self.cover_bytes = None
    else:
      self.cover_bytes = None

  def _load_tags(self) -> None:
    if self._mutagen_file.tags is not None:
      with contextlib.suppress(KeyError):
        if (_title := self._mutagen_file.tags["TIT2"].text[0]) is not None:
          self.props.title = _title

      with contextlib.suppress(KeyError):
        if (_artist := self._mutagen_file.tags["TPE1"].text[0]) is not None:
          self.props.artist = _artist

      with contextlib.suppress(KeyError):
        if (_album := self._mutagen_file.tags["TALB"].text[0]) is not None:
          self.props.album = _album

  def set_cover(self, img_path: Optional[str]) -> None:
    """Sets `self._mutagen_file` cover to specified image or removing it if image specified as `None`

    Parameters
    ----------
    img_path : str | None
        path to image or `None` if cover should be deleted
    """
    if img_path is not None:
      self.cover_bytes = open(img_path, "rb").read()  # noqa: SIM115
      if self._mutagen_file.tags:
        for tag in dict(self._mutagen_file.tags).copy():
          if tag.startswith("APIC"):
            del self._mutagen_file.tags[tag]
      else:
        self._mutagen_file.add_tags()

      self._mutagen_file.tags.add(
        APIC(
          encoding=3,
          mime="image/png",
          type=3,
          desc="Cover",
          data=self._cover,
        )
      )
      return
    if self._mutagen_file.tags:
      for tag in dict(self._mutagen_file.tags).copy():
        if tag.startswith("APIC"):
          del self._mutagen_file.tags[tag]

      self.cover_bytes = None

  def set_tag(  # noqa: D102
    self, tag_name: Literal["TITLE", "ARTIST", "ALBUM"], new_val: str
  ) -> None:
    _tag_name = Tag.determine("ID3", tag_name)
    if self._mutagen_file.tags is None:
      self._mutagen_file.add_tags()

    try:
      self._mutagen_file.tags[_tag_name].text[0] = new_val
    except (KeyError, IndexError):
      if _tag_name == "TIT2":
        self._mutagen_file.tags.add(TIT2(text=[new_val]))
      elif _tag_name == "TPE1":
        self._mutagen_file.tags.add(TPE1(text=[new_val]))
      elif _tag_name == "TALB":
        self._mutagen_file.tags.add(TALB(text=[new_val]))
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
        try:
          self._mutagen_file.tags["USLT"].text = text
        except KeyError:
          self._mutagen_file.tags.add(USLT(text=text))
        self.save()
      return

    with contextlib.suppress(KeyError):
      del self._mutagen_file.tags["USLT"]

    self.save()
