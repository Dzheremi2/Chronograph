import base64
import os
from typing import Union

import magic
from mutagen.flac import FLAC, Picture
from mutagen.flac import error as FLACError
from PIL import Image

from .file import BaseFile

tags_conjunction = {
    "TIT2": ["_title", "title"],
    "TPE1": ["_artist", "artist"],
    "TALB": ["_album", "album"],
}


class FileVorbis(BaseFile):
    """A Vorbis (ogg, flac) compatible file class. Inherited from `BaseFile`

    Parameters
    --------
    path : str
        A path to file for loading
    """

    __gtype_name__ = "FileVorbis"

    def __init__(self, path: str) -> None:
        super().__init__(path)

        self.load_cover()
        self.load_str_data()

    def load_cover(self) -> None:
        """Loads cover for Vorbis format audio"""
        if isinstance(self._mutagen_file, FLAC) and self._mutagen_file.pictures:
            if self._mutagen_file.pictures[0].data is not None:
                self._cover = self._mutagen_file.pictures[0].data
            else:
                self._cover = "icon"
        elif self._mutagen_file.get("metadata_block_picture", []):
            _data = None
            for base64_data in self._mutagen_file.get("metadata_block_picture", []):
                try:
                    _data = base64.b64decode(base64_data)
                except (TypeError, ValueError):
                    continue

                try:
                    _data = Picture(_data).data
                except FLACError:
                    continue

            if _data is None:
                self._cover = "icon"
            else:
                self._cover = _data
        else:
            self._cover = "icon"

    def load_str_data(self, tags: list = ["title", "artist", "album"]) -> None:
        """Loads title, artist and album for Vorbis media format

        Parameters
        ----------
        tags : list, persistent
            list of tags for parsing in vorbis comment, by default `["title", "artist", "album"]`
        """
        if self._mutagen_file.tags is not None:
            for tag in tags:
                try:
                    text = (
                        "Unknown"
                        if not self._mutagen_file.tags[tag.lower()][0]
                        else self._mutagen_file.tags[tag.lower()][0]
                    )
                    setattr(self, f"_{tag}", text)
                except KeyError:
                    try:
                        text = (
                            "Unknown"
                            if not self._mutagen_file.tags[tag.upper()][0]
                            else self._mutagen_file.tags[tag.upper()][0]
                        )
                        setattr(self, f"_{tag}", text)
                    except KeyError:
                        setattr(self, f"_{tag}", "Unknown")
        if self._title == "Unknown":
            self._title = os.path.basename(self._path)

    def set_cover(self, img_path: Union[str, None]) -> None:
        """Sets `self._mutagen_file` cover to specified image or removing it if image specified as `None`

        Parameters
        ----------
        img_path : str | None
            path to image or None if cover should be deleted
        """
        if img_path is not None:
            if isinstance(self._mutagen_file, FLAC):
                self._mutagen_file.clear_pictures()

            if "metadata_block_picture" in self._mutagen_file:
                self._mutagen_file["metadata_block_picture"] = []

            self._cover = data = open(img_path, "rb").read()

            picture = Picture()
            picture.data = data
            picture.mime = magic.from_file(img_path, mime=True)
            img = Image.open(img_path)
            picture.width = img.width
            picture.height = img.height

            if isinstance(self._mutagen_file, FLAC):
                self._mutagen_file.add_picture(picture)

            picture_data = picture.write()
            encoded_data = base64.b64encode(picture_data)
            vcomment_value = encoded_data.decode("ascii")
            if "metadata_block_picture" in self._mutagen_file:
                self._mutagen_file["metadata_block_picture"] = [
                    vcomment_value
                ] + self._mutagen_file["metadata_block_picture"]
            else:
                self._mutagen_file["metadata_block_picture"] = [vcomment_value]

        else:
            if isinstance(self._mutagen_file, FLAC):
                self._mutagen_file.clear_pictures()
                self._cover = "icon"

            if "metadata_block_picture" in self._mutagen_file:
                self._mutagen_file["metadata_block_picture"] = []
                self._cover = "icon"

    def set_str_data(self, tag_name: str, new_val: str) -> None:
        """Sets string tags to provided value

        Parameters
        ----------
        tag_name : str

        ::

            "TIT2" -> [_title, "title"]
            "TPE1" -> [_artist, "artist"]
            "TALB" -> [_album, "album"]

        new_val : str
            new value for setting
        """
        if tags_conjunction[tag_name][1].upper() in self._mutagen_file.tags:
            self._mutagen_file.tags[tags_conjunction[tag_name][1].upper()] = new_val
        else:
            self._mutagen_file.tags[tags_conjunction[tag_name][1]] = new_val
        setattr(self, tags_conjunction[tag_name][0], new_val)
