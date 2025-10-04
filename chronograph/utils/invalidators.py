"""Functions used in Gtk.ListBox and Gtk.FlowBox to invalidate sort or fliter"""

from typing import Union

from gi.repository import Adw, Gtk

from chronograph.internal import Constants
from chronograph.ui.widgets.song_card import SongCard
from chronograph.utils.miscellaneous import decode_filter_schema


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
    filter_decoded: tuple[bool] = (
        decode_filter_schema(0),
        decode_filter_schema(1),
        decode_filter_schema(2),
        decode_filter_schema(3),
    )
    child: Union[SongCard, Adw.ActionRow]
    if isinstance(child, Gtk.FlowBoxChild):
        child = child.get_child()
    try:
        # pylint: disable=protected-access
        if isinstance(child, SongCard):
            filter_allowed = filter_decoded[child._lyrics_file.highest_format]
        else:  # using `activatable-widget` as workaround to not create another one widget haha
            song_card: SongCard = child.get_activatable_widget().get_ancestor(SongCard)
            filter_allowed = filter_decoded[song_card._lyrics_file.highest_format]
        if not filter_allowed:
            return False

        text = Constants.WIN.search_entry.get_text().lower()
        text_matches = (
            text in child.get_title().lower() or text in child.get_subtitle().lower()
        )

        filtered = text != "" and not text_matches

        return not filtered

    except (AttributeError, IndexError):
        return True
