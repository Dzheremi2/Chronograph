"""Converters for timestamps"""

import re

from chronograph.internal import Schema
from chronograph.utils.miscellaneous import is_lrc
from chronograph.utils.wbw.elrc_parser import eLRCParser


def mcs_to_timestamp(mcs: int) -> str:
    """Convert microseconds to timestamp format"""
    ms = mcs // 1000  # get milliseconds
    match Schema.get("root.settings.syncing.precise"):
        case True:
            return f"[{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{ms % 1000:03d}] "
        case False:
            milliseconds = f"{ms % 1000:03d}"
            return (
                f"[{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{milliseconds[:-1]}] "
            )


def timestamp_to_mcs(text: str) -> int:
    """Convert timestamp format to microseconds

    Parameters
    ----------
    text : str
        A Line-by-Line lyrics line
    """
    pattern = r"\[([^\[\]]+)\]"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"No timestamp found in text: {text}")
    timestamp = match[0]
    pattern = r"(\d+):(\d+).(\d+)"
    mm, ss, ms = re.search(pattern, timestamp).groups()
    if len(ms) == 2:
        ms = ms + "0"
    total_ss = int(mm) * 60 + int(ss)
    total_ms = total_ss * 1000 + int(ms)
    return total_ms * 1000


def make_plain_lyrics(lyrics: str) -> str:
    """Creates a plain lyrics from Line-by-Line synced ones

    Parameters
    ----------
    lyrics : str
        Line-by-Line lyrics

    Returns
    -------
    str
        Plain lyrics
    """
    pattern = r"\[.*?\]"
    lyrics = lyrics.splitlines()
    plain_lyrics = []
    for line in lyrics:
        plain_lyrics.append(re.sub(pattern, "", line).strip())
    return "\n".join(plain_lyrics[:-1])


def lyrics_to_schema_preference(lyrics: str) -> str:
    target: str = Schema.get("root.settings.file-manipulation.embed-lyrics.default")

    if target == "elrc":
        if eLRCParser.is_elrc(lyrics):
            return lyrics
        target = "lrc"

    if target == "lrc":
        if not eLRCParser.is_elrc(lyrics):
            if is_lrc(lyrics):
                return lyrics
            target = "plain"
        else:
            lrc_lyrics = eLRCParser.to_plain_lrc(lyrics)
            return lrc_lyrics

    if target == "plain":
        if not eLRCParser.is_elrc(lyrics):
            if not is_lrc(lyrics):
                return lyrics
            return make_plain_lyrics(lyrics)
        lrc_lyrics = eLRCParser.to_plain_lrc(lyrics)
        return make_plain_lyrics(lrc_lyrics)
