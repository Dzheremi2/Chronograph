from typing import Union
import mutagen

from gi.repository import Gdk

class BaseFile:
    """A base class for mutagen filetypes classes

    Parameters
    ----------
    path : str
        A path to file for loading

    Props
    --------
    ::

        title : str -> Title of the song
        artist : str -> Artist of the song
        album : str -> Album of the song
        cover : Gdk.Texture | str -> Cover of the song
        path : str -> Path to the loaded song
        duration : float -> Duration of the loaded song
    """

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
    def load_str_data(self) -> None: ...
    def load_cover(self) -> None: ...
    def set_str_data(self) -> None: ...
    def set_cover(self) -> None: ...

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