from typing import Union

import mutagen
from gi.repository import Gdk
from .file import BaseFile

class FileID3(BaseFile):
    """A ID3 compatible file class. Inherited from `BaseFile`

    Parameters
    --------
    path : str
        A path to file for loading
    """

    # Inherited from BaseFile
    _title: str
    _artist: str
    _album: str
    _cover: Union[bytes, str]
    _mutagen_file: mutagen.FileType
    _duration: float
    _cover_updated: bool
    _path: str
    def save(self) -> None: ...
    def load_from_file(self, path: str) -> None: ...
    def get_cover_texture(self) -> Union[Gdk.Texture, str]: ...
    @property
    def title(self) -> str: ...
    @property
    def artist(self) -> str: ...
    @property
    def album(self) -> str: ...
    @property
    def cover(self) -> bytes: ...
    @property
    def path(self) -> str: ...
    @property
    def duration(self) -> int: ...

    def load_cover(self) -> None: ...
    def load_str_data(self) -> None: ...
    def set_cover(self, img_path: Union[str, None]) -> None: ...
    def set_str_data(self, tag_name: str, new_val: str) -> None: ...
