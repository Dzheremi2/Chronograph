from typing import Optional

import mutagen
from dgutils.decorators import baseclass
from gi.repository import Gdk, GdkPixbuf

from chronograph.internal import Constants


@baseclass
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

    _title: str = None
    _artist: str = None
    _album: str = None
    _cover: Optional[bytes] = None
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
        try:
            self._duration = self._mutagen_file.info.length
        except Exception:
            pass

    def get_cover_texture(self) -> Gdk.Texture:
        """Prepares a Gdk.Texture for setting to SongCard.paintable

        Returns
        -------
        Gdk.Texture
            Gdk.Texture or a placeholder texture if no cover is set
        """
        if self._cover:
            loader = GdkPixbuf.PixbufLoader.new()
            loader.write(self._cover)
            loader.close()
            pixbuf = loader.get_pixbuf()

            scaled_pixbuf = pixbuf.scale_simple(160, 160, GdkPixbuf.InterpType.BILINEAR)
            _texture = Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
            return _texture
        return Constants.COVER_PLACEHOLDER

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

    @property
    def duration_ns(self) -> int:
        return int(self._duration * 1_000_000_000) if self._duration else 0

    def compress_images(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def load_str_data(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def load_cover(self) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def set_str_data(self, tag_name: str, new_val: str) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError

    def set_cover(self, img_path: Optional[str]) -> None:
        """Should be implemented in file specific child classes"""
        raise NotImplementedError
