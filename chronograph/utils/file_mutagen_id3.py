import os
from typing import Union

from mutagen.id3 import APIC, TALB, TIT2, TPE1, ID3Tags

from .file import BaseFile

tags_conjunction = {"TIT2": "_title", "TPE1": "_artist", "TALB": "_album"}


class FileID3(BaseFile):
    """A ID3 compatible file class. Inherited from `BaseFile`

    Parameters
    --------
    path : str
        A path to file for loading
    """

    __gtype_name__ = "FileID3"

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.load_cover()
        self.load_str_data()

    # pylint: disable=attribute-defined-outside-init
    def load_cover(self) -> None:
        """Extracts cover from song file. If no cover, then sets cover as `icon`"""
        if self._mutagen_file.tags is not None:
            pictures = self._mutagen_file.tags.getall("APIC")
            if len(pictures) != 0:
                self._cover = pictures[0].data
            if len(pictures) == 0:
                self._cover = "icon"
        else:
            self._cover = "icon"

    def load_str_data(self) -> None:
        """Sets all string data from tags. If data is unavailable, then sets `Unknоwn`"""
        if self._mutagen_file.tags is not None:
            try:
                if (_title := self._mutagen_file.tags["TIT2"].text[0]) is not None:
                    self._title = _title
            except KeyError:
                self._title = os.path.basename(self._path)

            try:
                if (_artist := self._mutagen_file.tags["TPE1"].text[0]) is not None:
                    self._artist = _artist
            except KeyError:
                pass

            try:
                if (_album := self._mutagen_file.tags["TALB"].text[0]) is not None:
                    self._album = _album
            except KeyError:
                pass
        else:
            self._title = os.path.basename(self._path)

    def set_cover(self, img_path: Union[str, None]) -> None:
        """Sets `self._mutagen_file` cover to specified image or removing it if image specified as `None`

        Parameters
        ----------
        img_path : str | None
            path to image or None if cover should be deleted
        """
        if img_path is not None:
            self._cover = open(img_path, "rb").read()
            if self._mutagen_file.tags:
                for tag in dict(self._mutagen_file.tags).copy().keys():
                    if tag.startswith("APIC"):
                        del self._mutagen_file.tags[tag]
            else:
                self._mutagen_file.add_tags()

            self._mutagen_file.tags.add(
                APIC(
                    encoding=3,
                    mime="image/png",
                    type=3,
                    desc="Cover",
                    data=self._cover,
                )
            )
        else:
            if self._mutagen_file.tags:
                for tag in dict(self._mutagen_file.tags).copy().keys():
                    if tag.startswith("APIC"):
                        del self._mutagen_file.tags[tag]

            self._cover = "icon"

    def set_str_data(self, tag_name: str, new_val: str) -> None:
        """Sets string tags to provided value

        Parameters
        ----------
        tag_name : str

        ::

            "TIT2" -> _title
            "TPE1" -> _artist
            "TALB" -> _album

        new_val : str
            new value for setting
        """
        if self._mutagen_file.tags is None:
            self._mutagen_file.add_tags()

        try:
            self._mutagen_file.tags[tag_name].text[0] = new_val
        except (KeyError, IndexError):
            if tag_name == "TIT2":
                self._mutagen_file.tags.add(TIT2(text=[new_val]))
            elif tag_name == "TPE1":
                self._mutagen_file.tags.add(TPE1(text=[new_val]))
            elif tag_name == "TALB":
                self._mutagen_file.tags.add(TALB(text=[new_val]))
        setattr(self, tags_conjunction[tag_name], new_val)
