from typing import Optional, Self

from chronograph.backend.lyrics import Lyrics

from .file import BaseFile


class FileUntaggable(BaseFile):
  __gtype_name__ = "FileUntaggable"

  def __init__(self, path: str) -> None:
    super().__init__(path)

    self.cover = None

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> Self:  # noqa: ARG002
    return self
