from pathlib import Path

from gi.repository import GObject

from chronograph.internal import Schema
from chronograph.utils.lyrics.lyrics import Lyrics
from chronograph.utils.lyrics.lyrics_format import LyricsFormat


class LyricsFile(GObject.Object):
    """A controller for one media file's lyrics files.

    Parameters
    ----------
    media_bind_path : Path
        Path to the media file to which this lyrics file is bound.

    Emits
    ----------
    renamed : dict[str, Optional[dict[str, str]]]
        Emitted when the lyrics files are renamed.::

        {
            "elrc": {
                "old": str,
                "new": str
            } | None,
            "lrc": {
                "old": str,
                "new": str
            } | None
        }
    """

    __gtype_name__ = "LyricsFile"
    __gsignals__ = {
        "renamed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    elrc_path: str = GObject.Property(type=str, default="")
    lrc_path: str = GObject.Property(type=str, default="")
    highest_format: LyricsFormat = GObject.Property(type=int, default=0)

    def __init__(self, media_bind_path: Path) -> None:
        super().__init__()
        self._media_bind_path = media_bind_path

        # Dummy schema path to trigger initial path construction
        self._construct_paths(None, "root.settings.file-manipulation.elrc-prefix", None)
        Schema.connect("changed", self._construct_paths)

        # Setup Lyrics instances for each lyrics format
        if (path := Path(self.elrc_path)).exists(): 
            self.elrc_lyrics = Lyrics(path.read_text())
        else:
            self.elrc_lyrics = Lyrics("")
        self.elrc_lyrics.connect("save-triggered", self._save_lyrics)
        if (path := Path(self.lrc_path)).exists():
            self.lrc_lyrics = Lyrics(path.read_text())
        else:
            self.lrc_lyrics = Lyrics("")
        self.lrc_lyrics.connect("save-triggered", self._save_lyrics)

        self.set_property("highest-format", self._determine_highgest_format())
        self.elrc_lyrics.connect(
            "format-changed",
            lambda *_args: self.set_property(
                "highest_format", self._determine_highgest_format()
            ),
        )
        self.lrc_lyrics.connect(
            "format-changed",
            lambda *_args: self.set_property(
                "highest_format", self._determine_highgest_format()
            ),
        )

        # Setup previous paths to support renaming on LRC suffix/eLRC prefix change
        self._prev_elrc_path = Path(self.elrc_path)
        self._prev_lrc_path = Path(self.lrc_path)

        # Rename lyrics files on their paths change
        self.connect("notify::elrc-path", self._rename_file)
        self.connect("notify::lrc-path", self._rename_file)

    def _construct_paths(self, _schema, schema_path: str, _value) -> None:
        if schema_path in (
            "root.settings.file-manipulation.elrc-prefix",
            "root.settings.file-manipulation.format",
        ):
            lrc_suffix = Schema.get("root.settings.file-manipulation.format")
            elrc_prefix = Schema.get("root.settings.file-manipulation.elrc-prefix")
            lrc_path = self._media_bind_path.with_suffix(lrc_suffix)
            elrc_path = self._media_bind_path.with_name(
                elrc_prefix + self._media_bind_path.name
            ).with_suffix(lrc_suffix)

            self.set_property("lrc_path", str(lrc_path))
            self.set_property("elrc_path", str(elrc_path))

    def _determine_highgest_format(self) -> int:
        format_path_elrc = self.elrc_lyrics.format
        format_path_lrc = self.lrc_lyrics.format
        return max(format_path_elrc.value, format_path_lrc.value)

    def _rename_file(self, *_args) -> None:
        new_elrc_path = Path(self.elrc_path)
        new_lrc_path = Path(self.lrc_path)

        renamed_elrc = False
        renamed_lrc = False

        if self._prev_elrc_path != new_elrc_path:
            if self._prev_elrc_path.exists():
                self._prev_elrc_path.rename(new_elrc_path)
                renamed_elrc = True
            self._prev_elrc_path = new_elrc_path

        if self._prev_lrc_path != new_lrc_path:
            if self._prev_lrc_path.exists():
                self._prev_lrc_path.rename(new_lrc_path)
                renamed_lrc = True
            self._prev_lrc_path = new_lrc_path

        if any([renamed_elrc, renamed_lrc]):
            self.emit(
                "renamed",
                {
                    "elrc": (
                        {"old": str(self._prev_elrc_path), "new": str(new_elrc_path)}
                        if renamed_elrc
                        else None
                    ),
                    "lrc": (
                        {"old": str(self._prev_lrc_path), "new": str(new_lrc_path)}
                        if renamed_lrc
                        else None
                    ),
                },
            )

    def _save_lyrics(self, lyrics: Lyrics, file_content: str) -> None:
        """Save lyrics to the corresponding file based on the lyrics format."""
        if lyrics is self.elrc_lyrics:
            path = Path(self.elrc_path)
            path.write_text(file_content)
        elif lyrics is self.lrc_lyrics:
            path = Path(self.lrc_path)
            path.write_text(file_content)
        else:
            raise ValueError("Unknown lyrics instance provided for saving.")
