"""eLRC format parser"""

import re
from pathlib import Path
from typing import Optional

from chronograph.internal import Schema
from chronograph.utils.wbw.models.word_model import WordModel
from chronograph.utils.wbw.tokens import LineToken, WordToken


# pylint: disable=invalid-name
class eLRCParser:

    LINE_TIMESTAMP = re.compile(
        r"^\s*\[(?P<ts>(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{2,3}))?)\]\s*"
    )
    WORD_TIMESTAMP = re.compile(r"\s*<\d{2}:\d{2}(?:\.\d{2,3})?>\s*")
    TOKEN = re.compile(
        r"(?:<(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{2,3}))?>\s*)?(?P<word>[^\s<>]+)"
    )
    TIMESTAMP = re.compile(r"^\d{2}:\d{2}(?:\.\d{2,3})?$")

    _SPACER = "\u00a0"

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} may not be implemented")

    @staticmethod
    def _is_spacer(word: WordToken | WordModel) -> bool:
        return word.word == eLRCParser._SPACER * 20

    @staticmethod
    def _ms_from_parts(m: str, s: str, ms: Optional[str]) -> int:
        whole_ms = 0 if ms is None else (int(ms) if len(ms) == 3 else int(ms) * 10)
        return (int(m) * 60 + int(s)) * 1000 + whole_ms

    @staticmethod
    def parse_lines(data: Path | str) -> tuple[LineToken, ...]:
        """Generates a tuple of Separate `LineToken`s dataclasses

        Parameters
        ----------
        data : Path | str
            Path to a file or a string with all lyrics

        Returns
        -------
        tuple[LineToken, ...]
            `LineToken`s dataclasses tuple
        """

        def _strip_all_timestamps(string: str) -> str:
            # remove leading timestamp
            string = eLRCParser.LINE_TIMESTAMP.sub("", string, count=1)
            # remove all per-word timestamps
            string = eLRCParser.WORD_TIMESTAMP.sub(" ", string)
            # normalize whitespaces
            return " ".join(string.split())

        if isinstance(data, Path):
            lines = data.read_text(encoding="utf-8").splitlines()
        else:
            lines = data.splitlines()
        out: list[LineToken] = []

        for raw_line in lines:
            line = raw_line
            match = eLRCParser.LINE_TIMESTAMP.match(raw_line)

            if match:
                timestamp_str: str = match.group("ts")
                time_ms: int = eLRCParser._ms_from_parts(
                    match.group("m"), match.group("s"), match.group("ms")
                )
                cleaned_text: str = _strip_all_timestamps(raw_line)
                out.append(
                    LineToken(cleaned_text, line, time=time_ms, timestamp=timestamp_str)
                )
            else:
                cleaned_text: str = _strip_all_timestamps(raw_line)
                out.append(LineToken(cleaned_text, line))
        return tuple(out)

    @staticmethod
    def parse_words(line: LineToken | str) -> tuple[WordToken, ...]:
        """Generates a tuple of `WordToken`s dataclasses

        Parameters
        ----------
        line : LineToken | str
            A line to parse

        Returns
        -------
        tuple[WordToken, ...]
            Tuple of `WordToken` dataclasses
        """

        raw = line.line if hasattr(line, "line") else line
        pos = 0
        match = eLRCParser.LINE_TIMESTAMP.match(raw)
        if match:
            pos = match.end()

        tokens: list[WordToken] = []
        for token_match in eLRCParser.TOKEN.finditer(raw, pos):
            token_match: re.Match[str]
            word = token_match.group("word")
            m, s, ms = (
                token_match.group("m"),
                token_match.group("s"),
                token_match.group("ms"),
            )
            if m is not None:
                timestamp_str = f"{m}:{s}.{ms}"
                total_ms = eLRCParser._ms_from_parts(m, s, ms)
                tokens.append(WordToken(word, time=total_ms, timestamp=timestamp_str))
            else:
                tokens.append(WordToken(word))

        if not tokens:
            line_time: Optional[int] = None
            line_ts: Optional[str] = None
            if hasattr(line, "time"):
                try:
                    line_time = int(line)
                except Exception:
                    line_time = None
                line_ts = getattr(line, "timestamp", None) or None

            tokens.append(
                WordToken(eLRCParser._SPACER * 20, time=line_time, timestamp=line_ts)
            )

        return tuple(tokens)

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
    def _pick_timestamp_str(token: WordToken) -> Optional[str]:
        if token.timestamp and eLRCParser.TIMESTAMP.match(token.timestamp):
            return token.timestamp
        if token.time is not None and token.time >= 0:
            return eLRCParser._format_timestamp_ms(
                token.time, precise=Schema.get_precise_milliseconds()
            )
        return None

    @staticmethod
    def create_lyrics_elrc(lines: tuple[tuple["WordToken", ...], ...]) -> str:
        """Creates a string containing eLRC formatted lyrics

        Parameters
        ----------
        lines : tuple[tuple[WordToken, ...], ...]
            Lines in format of tuple og tuples (lines) of `WordToken`s

        Returns
        -------
        str
            eLRC formatted lyrics
        """
        out_lines: list[str] = []

        for line_tokens in lines:
            if not line_tokens:
                out_lines.append("")
                continue

            first = line_tokens[0]
            line_timestamp = eLRCParser._pick_timestamp_str(first)

            chunks: list[str] = []
            visible_count = 0
            for token in line_tokens:
                word = token.word
                if eLRCParser._is_spacer(token):
                    continue
                visible_count += 1
                timestamp = eLRCParser._pick_timestamp_str(token)
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

        return "\n".join(out_lines)

    @staticmethod
    def to_plain_lrc(data: Path | str) -> str:
        """Converts a given eLRC lyrics to plain LRC

        Parameters
        ----------
        data : Path | str
            A Path to eLRC lyrics file or lyrics itself

        Returns
        -------
        str
            Converted eLRC to LRC
        """
        lines = eLRCParser.parse_lines(data)
        out: list[str] = []
        for lt in lines:
            if lt.timestamp:
                out.append(f"[{lt.timestamp}]" + (f" {lt.text}" if lt.text else ""))
            else:
                out.append(lt.text)
        return "\n".join(out)

    @staticmethod
    def is_elrc(data: Path | str) -> bool:
        """Check if provided lyrics contain eLRC formatting (per-word timestamps).

        Parameters
        ----------
        data : Path | str
            Path to a file or lyrics string

        Returns
        -------
        bool
            True if the lyrics contain per-word timestamps (<mm:ss(.ms)>), False otherwise.
        """
        if isinstance(data, Path):
            text = data.read_text(encoding="utf-8")
        else:
            text = str(data)

        return bool(eLRCParser.WORD_TIMESTAMP.search(text))
