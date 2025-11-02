"""Converters for timestamps"""

import re

from chronograph.internal import Schema


def ns_to_timestamp(ns: int) -> str:
  """Convert microseconds to timestamp format"""
  ms = ns // 1_000_000  # get milliseconds
  match Schema.get("root.settings.syncing.precise"):
    case True:
      return f"[{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{ms % 1000:03d}] "
    case False:
      milliseconds = f"{ms % 1000:03d}"
      return f"[{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{milliseconds[:-1]}] "


def timestamp_to_ns(text: str) -> int:
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
  return total_ms * 1_000_000
