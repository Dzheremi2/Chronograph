from typing import Optional

from chronograph.backend.lyrics import Lyrics

from .file import BaseFile


class FileUntaggable(BaseFile):
  __gtype_name__ = "FileUntaggable"

  def __init__(self, path: str) -> None:
    super().__init__(path)

    self.cover = None

  def embed_lyrics(self, lyrics: Optional[Lyrics], *, force: bool = False) -> None:  # noqa: D102
    pass
