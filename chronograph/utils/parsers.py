"""Different parsers the app"""

from pathlib import Path
from typing import Union

from chronograph.internal import Schema
from chronograph.utils.file_backend.file_mutagen_id3 import FileID3
from chronograph.utils.file_backend.file_mutagen_mp4 import FileMP4
from chronograph.utils.file_backend.file_mutagen_vorbis import FileVorbis
from chronograph.utils.file_backend.file_untaggable import FileUntaggable


def parse_files(
    paths: tuple[str],
) -> tuple[Union[FileID3, FileVorbis, FileMP4, FileUntaggable]]:
    """Generates a tuple of mutagen files from a list of paths

    Parameters
    ----------
    paths : tuple[str]
        Paths to files

    Returns
    -------
    tuple[Union[FileID3, FileVorbis, FileMP4, FileUntaggable]]
        Returns a tuple of mutagen files or an empty tuple if no files
    """

    mutagen_files = []
    for path in paths:
        if Path(path).suffix in (".ogg", ".flac", ".opus"):
            mutagen_files.append(FileVorbis(path))
        elif Path(path).suffix in (".mp3", ".wav"):
            mutagen_files.append(FileID3(path))
        elif Path(path).suffix in (".m4a",):
            mutagen_files.append(FileMP4(path))
        elif Path(path).suffix in (".aac", ".AAC"):
            mutagen_files.append(FileUntaggable(path))

    return tuple(mutagen_files)


def parse_dir(path: str) -> tuple[str]:
    path = Path(path)
    files = []

    recursive = Schema.recursive_parsing
    follow_symlinks = Schema.follow_symlinks

    if not recursive:
        files = [str(f) for f in path.iterdir() if f.is_file()]
    else:
        for f in path.rglob("*"):
            if f.is_file() or (follow_symlinks and f.is_symlink()):
                files.append(str(f))
    return tuple(files)
