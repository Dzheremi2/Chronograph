import contextlib
from typing import Optional, Self

from mutagen.id3 import APIC, TALB, TIT2, TPE1, USLT

from chronograph.backend.lyrics import Lyrics, LyricsFormat
from chronograph.internal import Schema

from .file import TaggableFile

tags_conjunction = {"TIT2": "_title", "TPE1": "_artist", "TALB": "_album"}


class FileID3(TaggableFile):
  """An ID3 compatible file class. Inherited from `TaggableFile`

  Parameters
  ----------
  path : str
    A path to file for loading
  """

  __gtype_name__ = "FileID3"

  def load_cover(self) -> None:
    if self._mutagen_file.tags is not None:
      pictures = self._mutagen_file.tags.getall("APIC")
      if len(pictures) != 0:
        self._cover = pictures[0].data
      if len(pictures) == 0:
        self._cover = None
    else:
      self._cover = None

  def load_str_data(self) -> None:
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

  def set_cover(self, img_path: Optional[str]) -> Self:
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
      return self
    if self._mutagen_file.tags:
      for tag in dict(self._mutagen_file.tags).copy():
        if tag.startswith("APIC"):
          del self._mutagen_file.tags[tag]

      self._cover = None
    return self

  def set_str_data(self, tag_name: str, new_val: str) -> Self:
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
    return self

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> Self:
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
      return self

    with contextlib.suppress(KeyError):
      del self._mutagen_file.tags["USLT"]

    self.save()
    return self
