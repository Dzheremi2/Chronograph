import re
from typing import Optional

import yaml

from chronograph.backend.lyrics.chronie.chronie_lyrics import ChronieLyrics
from chronograph.backend.lyrics.interfaces import LyricFormat, LyricsConversionError

from .elrc import ElrcLyrics
from .lrc import LrcLyrics
from .merge import merge_lbl_chronie, merge_wbw_chronie
from .plain import PlainLyrics
from .tokens import chronie_from_tokens

FORMAT_ORDER = {"plain": 1, "lrc": 2, "elrc": 3}
_ELRC_HINT = re.compile(
  r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]\s*<\d{2}:\d{2}(?:\.\d{2,3})?>"
)
_LRC_HINT = re.compile(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")


def detect_lyric_format(text: str) -> LyricFormat:
  """Detect the most likely lyric format from text.

  Parameters
  ----------
  text : str
    Source lyrics text.

  Returns
  -------
  LyricFormat
    Parsed lyrics format instance.
  """
  chronie = _parse_chronie_yaml(text)
  if chronie is not None:
    return chronie
  if _ELRC_HINT.search(text):
    return ElrcLyrics(text)
  if _LRC_HINT.search(text):
    return LrcLyrics(text)
  return PlainLyrics(text)


def chronie_from_text(text: str) -> ChronieLyrics:
  """Convert text in any supported format to Chronie lyrics.

  Parameters
  ----------
  text : str
    Source lyrics text.

  Returns
  -------
  ChronieLyrics
    Parsed Chronie lyrics.
  """
  return detect_lyric_format(text).to_chronie()


def format_from_chronie(chronie: ChronieLyrics, fmt: str) -> LyricFormat:
  """Convert Chronie lyrics into a specific export format.

  Parameters
  ----------
  chronie : ChronieLyrics
    Chronie lyrics to convert.
  fmt : str
    Target format name.

  Returns
  -------
  LyricFormat
    Lyrics in the requested format.
  """
  fmt = fmt.lower()
  if fmt == "plain":
    return PlainLyrics.from_chronie(chronie)
  if fmt == "lrc":
    return LrcLyrics.from_chronie(chronie)
  if fmt == "elrc":
    return ElrcLyrics.from_chronie(chronie)
  if fmt == "chronie":
    return chronie
  raise LyricsConversionError(f"Unknown export format: {fmt}")


def export_chronie(chronie: ChronieLyrics, fmt: str) -> str:
  """Export Chronie lyrics into a requested format text.

  Parameters
  ----------
  chronie : ChronieLyrics
    Chronie lyrics to export.
  fmt : str
    Target format name.

  Returns
  -------
  str
    Text representation in the requested format.
  """
  return format_from_chronie(chronie, fmt).to_file_text()


def choose_export_format(chronie: ChronieLyrics, target: str) -> Optional[str]:
  """Pick a best available export format based on target preference.

  Parameters
  ----------
  chronie : ChronieLyrics
    Chronie lyrics to evaluate.
  target : str
    Preferred format name.

  Returns
  -------
  Optional[str]
    Selected export format name, or `None` if unavailable.
  """
  available = chronie.exportable_formats()
  if not available:
    return None
  target = target.lower()
  if target in available:
    return target
  target_rank = FORMAT_ORDER.get(target, 0)
  lower = [fmt for fmt in available if FORMAT_ORDER.get(fmt, 0) <= target_rank]
  if lower:
    return max(lower, key=lambda fmt: FORMAT_ORDER.get(fmt, 0))
  return max(available, key=lambda fmt: FORMAT_ORDER.get(fmt, 0))


def _parse_chronie_yaml(text: str) -> Optional[ChronieLyrics]:
  try:
    data = yaml.safe_load(text)
  except yaml.YAMLError:
    return None
  if not isinstance(data, list):
    return None
  for item in data:
    if not isinstance(item, dict) or "line" not in item:
      return None
  try:
    return ChronieLyrics.from_dicts(data)
  except ValueError:
    return None


__all__ = [
  "FORMAT_ORDER",
  "ElrcLyrics",
  "LrcLyrics",
  "PlainLyrics",
  "choose_export_format",
  "chronie_from_text",
  "chronie_from_tokens",
  "detect_lyric_format",
  "export_chronie",
  "format_from_chronie",
  "merge_lbl_chronie",
  "merge_wbw_chronie",
]
