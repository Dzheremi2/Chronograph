from chronograph.backend.lyrics.chronie import (
  ChronieLine,
  ChronieLyrics,
  ChronieTimings,
  ChronieWord,
)
from chronograph.backend.lyrics.formats.utils import is_spacer, token_start_ms
from chronograph.backend.wbw.tokens import WordToken


def chronie_from_tokens(lines: tuple[tuple[WordToken, ...], ...]) -> ChronieLyrics:
  """Convert WBW tokens into Chronie lyrics."""
  out_lines: list[ChronieLine] = []

  for line_tokens in lines:
    if not line_tokens:
      out_lines.append(ChronieLine(line=""))
      continue

    line_start = token_start_ms(line_tokens[0])
    line_timings = (
      ChronieTimings(start=line_start, end=None) if line_start is not None else None
    )

    words: list[ChronieWord] = []
    for token in line_tokens:
      if is_spacer(token):
        continue
      word_start = token_start_ms(token)
      word_timings = (
        ChronieTimings(start=word_start, end=None) if word_start is not None else None
      )
      words.append(ChronieWord(token.word, word_timings))

    words_val = words or None
    line_text = " ".join(word.word for word in words_val) if words_val else ""
    out_lines.append(ChronieLine(line=line_text, timings=line_timings, words=words_val))

  return ChronieLyrics(out_lines)
