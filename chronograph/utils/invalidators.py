"""Functions used in Gtk.ListBox and Gtk.FlowBox to invalidate sort or fliter"""

from typing import Union

from gi.repository import Gtk, Adw

from chronograph.internal import Constants
from chronograph.ui.widgets.song_card import SongCard


def invalidate_sort(
    child1: Union[Gtk.ListBoxRow, Gtk.FlowBoxChild],
    child2: Union[Gtk.ListBoxRow, Gtk.FlowBoxChild],
) -> int:
    """Function for determining the order of two children in Gtk.ListBox or Gtk.FlowBox

    Parameters
    ----------
    child1 : Union[Gtk.ListBoxRow, Gtk.FlowBoxChild]
        Row or Child #1 to compare
    child2 : Union[Gtk.ListBoxRow, Gtk.FlowBoxChild]
        Row or Child #2 to compare

    Returns
    -------
    int
        `-1` if `child1` should be before `child2`, `1` if `child1` should be after `child2`
    """
    child1: Union[SongCard, Adw.ActionRow]
    child2: Union[SongCard, Adw.ActionRow]
    if isinstance(child1, Gtk.FlowBoxChild):
        child1 = child1.get_child()
    if isinstance(child2, Gtk.FlowBoxChild):
        child2 = child2.get_child()
    order = None
    if Constants.WIN.sort_state == "a-z":
        order = False
    elif Constants.WIN.sort_state == "z-a":
        order = True

    return ((child1.get_title() > child2.get_title()) ^ order) * 2 - 1


def invalidate_filter(child: Union[Gtk.ListBoxRow, Gtk.FlowBoxChild]) -> bool:
    """Function for determining if a child should be visible in Gtk.ListBox or Gtk.FlowBox

    Parameters
    ----------
    child : Union[Gtk.ListBoxRow, Gtk.FlowBoxChild]
        Row or Child to check visibility

    Returns
    -------
    bool
        `True` if the child should be visible, `False` otherwise
    """
    child: Union[SongCard, Adw.ActionRow]
    if isinstance(child, Gtk.FlowBoxChild):
        child = child.get_child()
    try:
        text = Constants.WIN.search_entry.get_text().lower()
        filtered = text != "" and not (
            text in child.get_title().lower() or text in child.get_subtitle().lower()
        )
        return not filtered
    except AttributeError:
        return True
