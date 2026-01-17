from typing import Optional

from chronograph.backend.lyrics.chronie import ChronieLine, ChronieLyrics, ChronieWord
from chronograph.backend.lyrics.formats.utils import merge_timings


def merge_lbl_chronie(
  existing: Optional[ChronieLyrics], incoming: ChronieLyrics
) -> ChronieLyrics:
  """Merge line-level updates into Chronie, preserving word data and end timings."""
  if existing is None:
    return incoming

  merged_lines: list[ChronieLine] = []
  for idx, new_line in enumerate(incoming.lines):
    old_line = existing.lines[idx] if idx < len(existing.lines) else None
    if old_line is None:
      merged_lines.append(new_line)
      continue

    old_words = old_line.words or None
    words = old_words if old_words is not None else new_line.words
    start = new_line.timings.start if new_line.timings else None
    end = (
      new_line.timings.end
      if new_line.timings and new_line.timings.end is not None
      else (old_line.timings.end if old_line.timings else None)
    )
    timings = merge_timings(start, end)
    merged_lines.append(ChronieLine(line=new_line.line, timings=timings, words=words))

  return ChronieLyrics(merged_lines)


def merge_wbw_chronie(
  existing: Optional[ChronieLyrics], incoming: ChronieLyrics
) -> ChronieLyrics:
  """Merge word-level updates into Chronie, preserving end timings."""
  if existing is None:
    return incoming

  merged_lines: list[ChronieLine] = []
  for idx, new_line in enumerate(incoming.lines):
    old_line = existing.lines[idx] if idx < len(existing.lines) else None
    if old_line is None:
      merged_lines.append(new_line)
      continue

    line_start = new_line.timings.start if new_line.timings else None
    line_end = (
      new_line.timings.end
      if new_line.timings and new_line.timings.end is not None
      else (old_line.timings.end if old_line.timings else None)
    )
    timings = merge_timings(line_start, line_end)

    merged_words: Optional[list[ChronieWord]] = None
    if new_line.words:
      merged_words = []
      for w_idx, new_word in enumerate(new_line.words):
        old_word = (
          old_line.words[w_idx]
          if old_line.words and w_idx < len(old_line.words)
          else None
        )
        start = new_word.timings.start if new_word.timings else None
        end = (
          new_word.timings.end
          if new_word.timings and new_word.timings.end is not None
          else (old_word.timings.end if old_word and old_word.timings else None)
        )
        merged_words.append(ChronieWord(new_word.word, merge_timings(start, end)))
    elif old_line.words:
      merged_words = old_line.words

    merged_lines.append(
      ChronieLine(line=new_line.line, timings=timings, words=merged_words)
    )

  return ChronieLyrics(merged_lines)
