import contextlib
import re
from typing import Any

_TIMED_LINE_RE = re.compile(r"^(\[\d{2}:\d{2}\.\d{2,3}\])(\S)")
_TAG_PAIR_RE = re.compile(r"\[(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?P<val>.*?)\]")


def normalize_lines(text: str) -> list[str]:
  return [_TIMED_LINE_RE.sub(r"\1 \2", line) for line in text.splitlines()]


def join_meta(text: str, meta: dict[str, Any]) -> str:
  out_tags: list[str] = []
  for tag, val in meta.items():
    if tag == "length":
      str_length = _convert_length(val)
      out_tags.append(f"[{tag}:{str_length}]")
      continue

    if tag == "offset":
      str_offset = f"+{val}" if val >= 0 else f"-{val}"
      out_tags.append(f"[{tag}:{str_offset}]")
      continue

    out_tags.append(f"[{tag}:{val}]")

  tags_str = "\n".join(out_tags)
  return (tags_str + "\n" + text).strip()


def parse_meta(text: str) -> dict[str, Any]:
  out: dict[str, Any] = {}

  for line in text.splitlines():
    for tag in _TAG_PAIR_RE.finditer(line):
      key = tag.group("key").strip().lower()
      val = tag.group("val").strip()

      if key == "offset":
        with contextlib.suppress(ValueError):
          val = int(val)
      elif key == "length":
        with contextlib.suppress(ValueError):
          val = _convert_length(val)

      out[key] = val

  return out


def strip_meta(text: str) -> str:
  out: list[str] = []

  for line in text.splitlines():
    line = line.strip()
    if _TAG_PAIR_RE.match(line):
      continue
    out.append(line)
  return "\n".join(out).strip()


def _convert_length(length: str | int) -> str | int:
  if isinstance(length, str):
    length = length.strip()
    mm, ss = length.split(":")
    return (int(mm) * 60) + int(ss)

  if isinstance(length, int):
    mm, ss = divmod(length, 60)
    return f"{mm:02d}:{ss:02d}"

  raise TypeError("Only str and int are supported")
