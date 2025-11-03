"""Media files implementations for dirfferent tagging schemas"""

from .file import BaseFile
from .file_mutagen_id3 import FileID3
from .file_mutagen_mp4 import FileMP4
from .file_mutagen_vorbis import FileVorbis
from .file_untaggable import FileUntaggable

__all__ = ["BaseFile", "FileID3", "FileMP4", "FileUntaggable", "FileVorbis"]
