"""Different parsers for the app"""

from pathlib import Path
from typing import Iterable, Iterator, Optional, Union

from chronograph.backend.media.file import BaseFile
from chronograph.backend.media.file_mutagen_id3 import FileID3
from chronograph.backend.media.file_mutagen_mp4 import FileMP4
from chronograph.backend.media.file_mutagen_vorbis import FileVorbis
from chronograph.backend.media.file_untaggable import FileUntaggable


def parse_files(
  paths: Iterable[str],
) -> Iterator[BaseFile]:
  """Generates a tuple of mutagen files from a list of paths

  Parameters
  ----------
  paths : Iterable[str]
    Paths to files

  Returns
  -------
  Iterator[BaseFile]
    Returns a tuple of mutagen files or an empty tuple if no files
  """
  for file in paths:
    path = Path(file)
    suffix = path.suffix.lower()
    if suffix in (".ogg", ".flac", ".opus"):
      yield FileVorbis(file)
    if suffix in (".mp3", ".wav"):
      yield FileID3(file)
    if suffix in (".m4a",):
      yield FileMP4(file)
    if suffix in (".aac",):
      yield FileUntaggable(file)


def parse_file(file: Union[str, Path]) -> Optional[BaseFile]:
  """Generates a single mutagen file realization depending on file suffix

  Parameters
  ----------
  file : str
    Path to file

  Returns
  -------
  BaseFile
    Returns mutagen file realization or `None`
  """
  path = Path(file)
  suffix = path.suffix.lower()
  file = str(file)
  if suffix in (".ogg", ".flac", ".opus"):
    return FileVorbis(file)
  if suffix in (".mp3", ".wav"):
    return FileID3(file)
  if suffix in (".m4a",):
    return FileMP4(file)
  if suffix in (".aac",):
    return FileUntaggable(file)
  return None
