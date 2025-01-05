from typing import Union

import mutagen
from gi.repository import Gdk, GLib  # type: ignore


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
        duration : int -> Duration of the loaded song
    """

    __gtype_name__ = "BaseFile"

    _title: str = "Unknоwn"
    _artist: str = "Unknоwn"
    _album: str = "Unknоwn"
    _cover: Union[bytes, str] = None
    _mutagen_file: mutagen.FileType = None
    _duration: float = None
    _cover_updated: bool = False

    def __init__(self, path: str) -> None:
        self._path: str = path
        self.load_from_file(path)

    def save(self) -> None:
        """Saves the changes to the file"""
        self._mutagen_file.save()

    def load_from_file(self, path: str) -> None:
        """Generates mutagen file instance for path

        Parameters
        ----------
        path : str
            /path/to/file
        """
        self._mutagen_file = mutagen.File(path)
        self._duration = self._mutagen_file.info.length

    def get_cover_texture(self) -> Union[Gdk.Texture, str]:
        """Prepares a Gdk.Texture for setting to SongCard.paintable

        Returns
        -------
        Gdk.Texture | str
            Gdk.Texture or 'icon' string if no cover
        """
        if not self._cover == "icon":
            _bytes = GLib.Bytes(self._cover)
            _texture = Gdk.Texture.new_from_bytes(_bytes)
            return _texture
        else:
            return "icon"

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def artist(self) -> str:
        return self._artist

    @artist.setter
    def artist(self, value: str) -> None:
        self._artist = value

    @property
    def album(self) -> str:
        return self._album

    @album.setter
    def album(self, value: str) -> None:
        self._album = value

    @property
    def cover(self) -> bytes:
        return self._cover

    @cover.setter
    def cover(self, data: bytes) -> None:
        self._cover = data

    @property
    def path(self) -> str:
        return self._path

    @property
    def duration(self) -> int:
        return round(self._duration)

    def load_str_data(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def load_cover(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def set_str_data(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def set_cover(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError
