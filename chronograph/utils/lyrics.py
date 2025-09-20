import re
from enum import Enum
from typing import Literal, Optional

from chronograph.internal import Schema
from chronograph.utils.wbw.models.word_model import WordModel
from chronograph.utils.wbw.token_parser import TokenParser
from chronograph.utils.wbw.tokens import WordToken


class LyricsHierarchyConversion(Exception):
    """Raised if target lyrics format is hierarchically higher than lyrics format itself.

    Hierarchy::

        ELRC -> LRC -> PLAIN
    """

    def __init__(
        self, message="Target format is hierarchically higher than the source lyrics."
    ):
        super().__init__(message)


class LyricsFormat(Enum):
    """Lyrics format enum

    ::

        PLAIN -> 0
        LRC -> 1
        ELRC -> 2
    """
    PLAIN = 0
    LRC = 1
    ELRC = 2

    @classmethod
    def from_int(cls, member_id: Literal[0, 1, 2]) -> "LyricsFormat":
        for member in cls:
            if member.value == member_id:
                return member
        raise TypeError(f"Provided ID of {member_id} is out of scope of LyricsFormat")



class Lyrics:
    """A lyrics representing class with useful methods.

    Parameters
    ----------
    text : str
        Text of lyrics
    """

    LINE_TIMESTAMP = re.compile(
        r"^\s*\[(?P<ts>(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{2,3}))?)\]\s*"
    )
    WORD_TIMESTAMP = re.compile(r"\s*<\d{2}:\d{2}(?:\.\d{2,3})?>\s*")
    TOKEN = re.compile(
        r"(?:<(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{2,3}))?>\s*)?(?P<word>[^\s<>]+)"
    )
    TIMESTAMP = re.compile(r"^\d{2}:\d{2}(?:\.\d{2,3})?$")

    _SPACER = "\u00a0"

    def __init__(self, text: str) -> None:
        self._lyrics = text
        self._format = self._detect_format()

    def __bool__(self) -> bool:
        if self._lyrics:
            return True
        return False

    @classmethod
    def from_tokens(cls, lines: tuple[tuple[WordToken, ...], ...]) -> "Lyrics":
        """Creates a new instance of `self` from `WordToken`s. Suitable only for eLRC

        Parameters
        ----------
        lines : tuple[tuple[WordToken, ...], ...]
            Lines of lyrics in format of tuple(lines) of tuples(words) of `WordToken`s

        Returns
        -------
        Lyrics
            A new instance of `self`
        """
        out_lines: list[str] = []

        for line_tokens in lines:
            if not line_tokens:
                out_lines.append("")
                continue

            first = line_tokens[0]
            line_timestamp = cls._pick_timestamp_str(first)

            chunks: list[str] = []
            visible_count = 0
            for token in line_tokens:
                word = token.word
                if cls._is_spacer(token):
                    continue
                visible_count += 1
                timestamp = cls._pick_timestamp_str(token)
                if timestamp:
                    chunks.append(f"<{timestamp}> {word}")
                else:
                    chunks.append(word)

            if visible_count > 0:
                if line_timestamp:
                    out_lines.append(f"[{line_timestamp}] " + " ".join(chunks))
                else:
                    out_lines.append(" ".join(chunks))
            else:
                out_lines.append(f"[{line_timestamp}]" if line_timestamp else "")

        return cls("\n".join(out_lines))

    def to_format(self, target: LyricsFormat) -> None:
        """Converts lyrics to a target format if hierarchy allows.

        Parameters
        ----------
        target : LyricsFormat
            Target format of lyrics

        Raises
        ------
        LyricsHierarchyConversion
            Raised if lyrics couldn't be converted to target format
        """
        if self._format.value > target.value:
            raise LyricsHierarchyConversion(
                f"Cannot convert from {self._format.name} to {target.name}. "
                "Conversion is only possible down the hierarchy."
            )

        if self._format == target:
            return

        if self._format == LyricsFormat.LRC and target == LyricsFormat.PLAIN:
            self._lyrics = self._to_plain()
            self._format = LyricsFormat.PLAIN

        if self._format == LyricsFormat.ELRC:
            if target == LyricsFormat.LRC:
                self._lyrics = self._to_lrc()
                self._format = LyricsFormat.LRC
            elif target == LyricsFormat.PLAIN:
                self._lyrics = self._to_plain_from_elrc()
                self._format = LyricsFormat.PLAIN

    def of_format(self, target: LyricsFormat) -> str:
        """Returns lyrics converted to a specified format without rewriting them.

        Parameters
        ----------
        target : LyricsFormat
            Target format of lyrics

        Returns
        -------
        str
            Converted lyrics

        Raises
        ------
        LyricsHierarchyConversion
            Raised if lyrics couldn't be converted to target format
        """
        if target.value > self._format.value:
            raise LyricsHierarchyConversion(
                f"Cannot convert from {self._format.name} to {target.name}. "
                "Conversion is only possible down the hierarchy."
            )

        if target.value == self._format.value:
            return self._lyrics

        if self._format == LyricsFormat.LRC and target == LyricsFormat.PLAIN:
            return self._to_plain()

        if self._format == LyricsFormat.ELRC:
            if target == LyricsFormat.LRC:
                return self._to_lrc()
            if target == LyricsFormat.PLAIN:
                return self._to_plain_from_elrc()

    def _detect_format(self) -> LyricsFormat:
        if re.search(
            r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]\s*<\d{2}:\d{2}(?:\.\d{2,3})?>",
            self._lyrics,
        ):
            return LyricsFormat.ELRC
        if re.search(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]", self._lyrics):
            return LyricsFormat.LRC
        return LyricsFormat.PLAIN

    def _to_lrc(self) -> str:
        lines = TokenParser.parse_lines(self._lyrics)
        out = []
        for line in lines:
            if line.timestamp:
                out.append(f"[{line.timestamp}] {line.text}".strip())
            else:
                out.append(line.text)
        return "\n".join(out)

    def _to_plain(self) -> str:
        pattern = r"\[.*?\]"
        plain_lines = [
            re.sub(pattern, "", line).strip() for line in self._lyrics.splitlines()
        ]
        return "\n".join(plain_lines)

    def _to_plain_from_elrc(self) -> str:
        lrc_text = self._to_lrc()
        lyrics_obj = Lyrics(lrc_text)
        return lyrics_obj._to_plain()  # pylint: disable=protected-access

    @property
    def lyrics(self) -> str:
        return self._lyrics

    @lyrics.setter
    def lyrics(self, new_text: str) -> None:
        self._lyrics = new_text
        self._format = self._detect_format()

    @property
    def format(self) -> LyricsFormat:
        return self._format

    @staticmethod
    def _pick_timestamp_str(token: WordToken) -> Optional[str]:
        if token.timestamp and Lyrics.TIMESTAMP.match(token.timestamp):
            return token.timestamp
        if token.time is not None and token.time >= 0:
            return Lyrics._format_timestamp_ms(
                token.time, precise=Schema.get("root.settings.syncing.precise")
            )
        return None

    @staticmethod
    def _format_timestamp_ms(ms: int, *, precise: bool = True) -> str:
        m = ms // 60000
        s = (ms % 60000) // 1000
        sub = ms % 1000
        return (
            f"{m:02d}:{s:02d}.{sub:03d}"
            if precise
            else f"{m:02d}:{s:02d}.{str(sub).zfill(3)[:-1]}"
        )

    @staticmethod
    def _is_spacer(word: WordToken | WordModel) -> bool:
        return word.word == Lyrics._SPACER * 20
