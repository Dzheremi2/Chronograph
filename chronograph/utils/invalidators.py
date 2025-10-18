"""Functions used in Gtk.ListBox and Gtk.FlowBox to invalidate sort or fliter"""

from gi.repository import Gtk

from chronograph.internal import Constants
from chronograph.ui.widgets.song_card import SongCard
from chronograph.utils.miscellaneous import decode_filter_schema


def invalidate_sort_flowbox(child1: Gtk.FlowBoxChild, child2: Gtk.FlowBoxChild) -> int:
  """Function for determining the order of two children in Gtk.FlowBox

  Parameters
  ----------
  child1 : Gtk.FlowBoxChild
    Child #1 to compare
  child2 : Gtk.FlowBoxChild
    Child #2 to compare

  Returns
  -------
  int
    `-1` if `child1` should be before `child2`, `1` if `child1` should be after `child2`
  """
  child1: SongCard
  child2: SongCard
  if isinstance(child1, Gtk.FlowBoxChild):
    child1 = child1.get_child()
  if isinstance(child2, Gtk.FlowBoxChild):
    child2 = child2.get_child()
  order = None
  if Constants.WIN.sort_state == "a-z":
    order = False
  elif Constants.WIN.sort_state == "z-a":
    order = True

  return ((child1.model.title_display > child2.model.title_display) ^ order) * 2 - 1


def invalidate_filter_flowbox(child: Gtk.FlowBoxChild) -> bool:
  """Function for determining if a child should be visible in Gtk.ListBox or Gtk.FlowBox

  Parameters
  ----------
  child : Gtk.FlowBoxChild
    Child to check visibility

  Returns
  -------
  bool
    `True` if the child should be visible, `False` otherwise
  """
  filter_decoded: tuple[bool] = (
    decode_filter_schema(0),
    decode_filter_schema(1),
    decode_filter_schema(2),
    decode_filter_schema(3),
  )
  child: SongCard
  child = child.get_child()
  try:
    filter_allowed = filter_decoded[child.model.lyrics_file.highest_format]
    if not filter_allowed:
      return False

    text = Constants.WIN.search_entry.get_text().lower()
    text_matches = (
      text in child.model.title_display.lower()
      or text in child.model.artist_display.lower()
    )

    filtered = text != "" and not text_matches

    return not filtered

  except (AttributeError, IndexError):
    return True


def invalidate_sort_listbox(row1: Gtk.ListBoxRow, row2: Gtk.ListBoxRow) -> int:
  """Function for determining the order of two children in Gtk.ListBox

  Parameters
  ----------
  row1 : Gtk.ListBoxRow
    Child #1 to compare
  row2 : Gtk.ListBoxRow
    Child #2 to compare

  Returns
  -------
  int
    `-1` if `child1` should be before `child2`, `1` if `child1` should be after `child2`
  """
  order = None
  if Constants.WIN.sort_state == "a-z":
    order = False
  elif Constants.WIN.sort_state == "z-a":
    order = True

  return ((row1.get_title() > row2.get_title()) ^ order) * 2 - 1


def invalidate_filter_listbox(row: Gtk.ListBoxRow) -> bool:
  """Function for determining if a child should be visible in Gtk.ListBox or Gtk.ListBox

  Parameters
  ----------
  row : Gtk.ListBoxRow
    Row to check visibility

  Returns
  -------
  bool
    `True` if the child should be visible, `False` otherwise
  """
  filter_decoded: tuple[bool] = (
    decode_filter_schema(0),
    decode_filter_schema(1),
    decode_filter_schema(2),
    decode_filter_schema(3),
  )
  try:
    song_card: SongCard = row.get_activatable_widget().get_ancestor(SongCard)
    filter_allowed = filter_decoded[song_card.model.lyrics_file.highest_format]
    if not filter_allowed:
      return False

    text = Constants.WIN.search_entry.get_text().lower()
    text_matches = text in row.get_title().lower() or text in row.get_subtitle().lower()

    filtered = text != "" and not text_matches

    return not filtered

  except (AttributeError, IndexError):
    return True
