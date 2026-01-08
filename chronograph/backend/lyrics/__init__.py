"""Lyrics related module"""

from .formats import ElrcLyrics, LrcLyrics, PlainLyrics, detect_start_lyrics
from .interfaces import EndLyrics, LyricsConversionError, StartLyrics
from .store import (
  delete_track_lyric,
  get_track_lyric,
  get_track_lyrics,
  save_track_lyric,
)

__all__ = [
  "ElrcLyrics",
  "EndLyrics",
  "LrcLyrics",
  "LyricsConversionError",
  "PlainLyrics",
  "StartLyrics",
  "delete_track_lyric",
  "detect_start_lyrics",
  "get_track_lyric",
  "get_track_lyrics",
  "save_track_lyric",
]
