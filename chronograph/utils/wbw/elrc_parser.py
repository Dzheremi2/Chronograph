"""eLRC format parser"""

import re
from pathlib import Path
from typing import Optional

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

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} may not be implemented")

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
        tuple[LineToken]
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
                out.append(LineToken(cleaned_text, line, time_ms, timestamp_str))
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
        tuple[WordToken]
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
                tokens.append(WordToken(word, total_ms, timestamp_str))
            else:
                tokens.append(WordToken(word))

        return tuple(tokens)
