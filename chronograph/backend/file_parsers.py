"""Different parsers for the app"""

import os
from pathlib import Path
from typing import Iterable, Iterator, Optional, Union

from chronograph.backend.media.file import BaseFile
from chronograph.backend.media.file_mutagen_id3 import FileID3
from chronograph.backend.media.file_mutagen_mp4 import FileMP4
from chronograph.backend.media.file_mutagen_vorbis import FileVorbis
from chronograph.backend.media.file_untaggable import FileUntaggable
from chronograph.internal import Schema


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
    if path.suffix in (".ogg", ".flac", ".opus"):
      yield FileVorbis(file)
    if path.suffix in (".mp3", ".wav"):
      yield FileID3(file)
    if path.suffix in (".m4a",):
      yield FileMP4(file)
    if path.suffix in (".aac", ".AAC"):
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
  if path.suffix in (".ogg", ".flac", ".opus"):
    return FileVorbis(file)
  if path.suffix in (".mp3", ".wav"):
    return FileID3(file)
  if path.suffix in (".m4a",):
    return FileMP4(file)
  if path.suffix in (".aac", ".AAC"):
    return FileUntaggable(file)
  return None


def parse_dir(path: str) -> tuple[str, ...]:
  """Resolves all directory content paths depending on user settings

  Parameters
  ----------
  path : str
    root directory path

  Returns
  -------
  tuple[str]
    tuple of leaf paths
  """
  path: Path = Path(path)
  files = []

  recursive = Schema.get("root.settings.general.recursive-parsing.enabled")
  follow_symlinks = Schema.get(
    "root.settings.general.recursive-parsing.follow-symlinks"
  )

  if not recursive:
    files = [str(f) for f in path.iterdir() if f.is_file()]
  else:
    for dirpath, __, filenames in os.walk(str(path), followlinks=follow_symlinks):
      current_dir_path = Path(dirpath)

      for filename in filenames:
        full_path = current_dir_path / filename

        if full_path.is_file() or full_path.is_symlink():
          files.append(str(full_path))
  return tuple(files)
