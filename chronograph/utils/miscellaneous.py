"""Some functions without a specific grouping"""

import os
from pathlib import Path
from typing import Optional

from chronograph.internal import Schema


def get_common_directory(paths: tuple[str]) -> Optional[str]:
  """Return a common directory for provided paths or `None`.

  Parameters
  ----------
  paths : tuple[str]
      Paths to files

  Returns
  -------
  Optional[str]
      Common directory path or `None` if not in the same tree
  """
  dirs = [Path(Path(p).resolve()).parent for p in paths]
  common = os.path.commonpath(dirs)
  for p in dirs:
    if not Path(p).is_relative_to(Path(common)):
      return None
  return common


def decode_filter_schema(index: int) -> bool:
  """Gets a filter value of a provided id

  Parameters
  ----------
  index : int
      index of filter in filter string in Schema

  Returns
  -------
  bool
      value of this filter
  """
  value = Schema.get("root.state.library.filter")
  try:
    return bool(int(value.split(":")[index]))
  except (IndexError, ValueError):
    return True


def encode_filter_schema(none: bool, plain: bool, lrc: bool, elrc: bool) -> str:
  """Encode filter states into a string for schema storage.

  Parameters
  ----------
  none : bool
      State of 'none' filter
  plain : bool
      State of 'plain' filter
  lrc : bool
      State of 'lrc' filter
  elrc : bool
      State of 'elrc' filter

  Returns
  -------
  str
      Encoded filter state string
  """
  return f"{int(none)}:{int(plain)}:{int(lrc)}:{int(elrc)}"
