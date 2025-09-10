import base64
import io
import os
from typing import Optional, Union

import magic
from mutagen.flac import FLAC, Picture
from mutagen.flac import error as FLACError
from PIL import Image

from chronograph.internal import Schema
from chronograph.utils.converter import lyrics_to_schema_preference, make_plain_lyrics
from chronograph.utils.wbw.elrc_parser import eLRCParser

from .file import TaggableFile

tags_conjunction = {
    "TIT2": ["_title", "title"],
    "TPE1": ["_artist", "artist"],
    "TALB": ["_album", "album"],
}


# pylint: disable=attribute-defined-outside-init
class FileVorbis(TaggableFile):
    """A Vorbis (ogg, flac) compatible file class. Inherited from `TaggableFile`

    Parameters
    --------
    path : str
        A path to file for loading
    """

    __gtype_name__ = "FileVorbis"

    def compress_images(self) -> None:
        if Schema.get_load_compressed_covers():
            quality = Schema.get_compress_level()
            pic: Union[Picture, None] = None

            if isinstance(self._mutagen_file, FLAC) and self._mutagen_file.pictures:
                pic = self._mutagen_file.pictures[0]
            else:
                encoded_blocks = self._mutagen_file.get("metadata_block_picture", [])
                for base64_data in encoded_blocks:
                    try:
                        pic = Picture(base64.b64decode(base64_data))
                        break
                    except FLACError:
                        continue

            if not pic or not pic.data:
                return

            with Image.open(io.BytesIO(pic.data)) as img:
                buffer = io.BytesIO()
                img.convert("RGB").save(
                    buffer, format="JPEG", quality=quality, optimize=True
                )
                bytes_compressed = buffer.getvalue()

            pic.data = bytes_compressed
            pic.mime = "image/jpeg"

            if isinstance(self._mutagen_file, FLAC):
                self._mutagen_file.clear_pictures()
                self._mutagen_file.add_picture(pic)

            picture_data = pic.write()
            encoded = base64.b64encode(picture_data).decode("ascii")
            self._mutagen_file["metadata_block_picture"] = [encoded]

            self._cover = bytes_compressed

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
                self._cover = None
            else:
                self._cover = _data
        else:
            self._cover = None

    # pylint: disable=dangerous-default-value
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
        if self._title == "Unknown":  # pylint: disable=access-member-before-definition
            self._title = os.path.basename(self._path)

    def set_cover(self, img_path: Optional[str]) -> None:
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
                self._cover = None

            if "metadata_block_picture" in self._mutagen_file:
                self._mutagen_file["metadata_block_picture"] = []
                self._cover = None

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

    def embed_lyrics(self, lyrics: str):
        if Schema.get_embed_lyrics():
            lyrics = lyrics_to_schema_preference(lyrics)
            if not Schema.get_use_individual_synced_tag_vorbis():
                self._mutagen_file.tags["UNSYNCEDLYRICS"] = lyrics
            else:
                if eLRCParser.is_elrc(lyrics):
                    self._mutagen_file.tags["UNSYNCEDLYRICS"] = make_plain_lyrics(
                        eLRCParser.to_plain_lrc(lyrics)
                    )
                else:
                    self._mutagen_file.tags["UNSYNCEDLYRICS"] = make_plain_lyrics(
                        lyrics
                    )

                self._mutagen_file.tags["LYRICS"] = lyrics
            self.save()
