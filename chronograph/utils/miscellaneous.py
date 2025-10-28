"""Some functions without a specific grouping"""

from chronograph.internal import Schema


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
