import re
from pathlib import Path
from typing import Any, Sequence, Union


class LyricsFile:
    """Helper class for easier LRC files control with LRC metatags support

    Parameters
    -------
    path : Path | str
        /path/to/lrc/file
    """

    _TAG_PAIR_RE = re.compile(r"\[(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?P<val>.*?)\]")
    _TIMED_LINE_RE = re.compile(r"^(\[\d{2}:\d{2}\.\d{2,3}\])(\S)")

    meta: dict
    lyrics: str

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if not self.path.exists():
            with open(self.path, "w"):
                pass
        self.meta = self._parse_meta()
        self.lyrics = self._strip_tags()

    def _strip_tags(self) -> str:
        out: list = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if self._TAG_PAIR_RE.match(line):
                continue
            out.append(line)
        return "\n".join(out).strip()

    def get_normalized_lines(self) -> list[str]:
        """Returns normalized lyrics with whitespaces after the timestamp"""
        return [
            self._TIMED_LINE_RE.sub(r"\1 \2", line) for line in self.lyrics.splitlines()
        ]

    def _convert_length(self, lenght: Union[str, int]) -> Union[str, int]:
        if isinstance(lenght, str):
            lenght = lenght.strip()
            mm, ss = lenght.split(":")
            return (int(mm) * 60) + int(ss)

        if isinstance(lenght, int):
            mm, ss = divmod(lenght, 60)
            return f"{mm:02d}:{ss:02d}"

        raise TypeError("Only str and int are supported")

    def _parse_meta(self) -> dict[str, Any]:
        out: dict[str, Any] = {}

        for line in self.path.read_text():
            for tag in self._TAG_PAIR_RE.finditer(line):
                key = tag.group("key").strip().lower()
                val = tag.group("val").strip()

                if key == "offset":
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                elif key == "length":
                    try:
                        val = self._convert_length(val)
                    except Exception:
                        pass

                out[key] = val

        return out

    def _construct_file(self) -> str:
        out_tags: list[str] = []
        for tag, val in self.meta.items():
            if tag == "length":
                str_length = self._convert_length(val)
                out_tags.append(f"[{tag}:{str_length}]")
                continue

            if tag == "offset":
                if val >= 0:
                    str_offset = f"+{val}"
                else:
                    str_offset = f"-{val}"
                out_tags.append(f"[{tag}:{str_offset}]")
                continue

            out_tags.append(f"[{tag}:{val}]")

        tags_str = "\n".join(out_tags)
        file_str = (tags_str + "\n" + self.lyrics).strip()
        return file_str

    def save(self) -> None:
        """Saves the metatags and lyrics of the LRC to file"""
        self.path.write_text(self._construct_file())

    def modify_tags(self, tags_seq: Sequence[tuple[str, Union[str, int]]]) -> None:
        """Sets the given tags to a given values

        Parameters
        ----------
        tags_seq : Sequence[tuple[str, Union[str, int]]]
            A sequence of pairs of `("key", value)` type
        """
        for key, val in tags_seq:
            key = key.lower()
            if key == "length" and isinstance(val, str):
                val = self._convert_length(val)

            if key == "offset":
                val = int(val)

            self.meta[key] = val

        self.save()

    def modify_lyrics(self, lyrics: str) -> None:
        """Sets the lyrics of the file to a provided text

        Parameters
        ----------
        lyrics : str
            Lyrics text (no matter LRC or eLRC)
        """
        self.lyrics = lyrics
        self.save()
