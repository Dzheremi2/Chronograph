import contextlib
import io
from typing import Optional

from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, USLT
from PIL import Image

from chronograph.backend.lyrics import Lyrics, LyricsFormat
from chronograph.internal import Schema

from .file import TaggableFile

tags_conjunction = {"TIT2": "_title", "TPE1": "_artist", "TALB": "_album"}


class FileID3(TaggableFile):
  """A ID3 compatible file class. Inherited from `TaggableFile`

  Parameters
  ----------
  path : str
      A path to file for loading
  """

  __gtype_name__ = "FileID3"

  def compress_images(self) -> None:
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

  def load_cover(self) -> None:
    """Extracts cover from song file. If no cover, then sets cover as `icon`"""
    if self._mutagen_file.tags is not None:
      pictures = self._mutagen_file.tags.getall("APIC")
      if len(pictures) != 0:
        self._cover = pictures[0].data
      if len(pictures) == 0:
        self._cover = None
    else:
      self._cover = None

  def load_str_data(self) -> None:
    """Sets all string data from tags. If data is unavailable, then sets `Unknown`"""
    if self._mutagen_file.tags is not None:
      try:
        if (_title := self._mutagen_file.tags["TIT2"].text[0]) is not None:
          self._title = _title
      except KeyError:
        pass

      try:
        if (_artist := self._mutagen_file.tags["TPE1"].text[0]) is not None:
          self._artist = _artist
      except KeyError:
        pass

      try:
        if (_album := self._mutagen_file.tags["TALB"].text[0]) is not None:
          self._album = _album
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
      self._cover = open(img_path, "rb").read()  # noqa: SIM115
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

      self._cover = None

  def set_str_data(self, tag_name: str, new_val: str) -> None:
    """Sets string tags to provided value

    Parameters
    ----------
    tag_name : str

    ::

        "TIT2" -> _title
        "TPE1" -> _artist
        "TALB" -> _album

    new_val : str
        new value for setting
    """
    if self._mutagen_file.tags is None:
      self._mutagen_file.add_tags()

    try:
      self._mutagen_file.tags[tag_name].text[0] = new_val
    except (KeyError, IndexError):
      if tag_name == "TIT2":
        self._mutagen_file.tags.add(TIT2(text=[new_val]))
      elif tag_name == "TPE1":
        self._mutagen_file.tags.add(TPE1(text=[new_val]))
      elif tag_name == "TALB":
        self._mutagen_file.tags.add(TALB(text=[new_val]))
    setattr(self, tags_conjunction[tag_name], new_val)

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
