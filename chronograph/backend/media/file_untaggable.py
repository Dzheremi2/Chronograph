from typing import Optional, Self

from chronograph.backend.lyrics import ChronieLyrics

from .file import BaseFile


class FileUntaggable(BaseFile):
  __gtype_name__ = "FileUntaggable"

  def __init__(self, path: str) -> None:
    super().__init__(path)
    self.cover = None

  def embed_lyrics(self, lyrics: Optional[ChronieLyrics], target: str) -> Self:  # noqa: ARG002
    return self
