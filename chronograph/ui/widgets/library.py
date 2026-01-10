import contextlib
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from gi.repository import Gdk, Gio, GLib, Gtk

from chronograph.backend.file.available_lyrics import AvailableLyrics
from chronograph.backend.file.library_manager import LibraryManager
from chronograph.backend.file.song_card_model import SongCardModel
from chronograph.backend.file_parsers import parse_file
from chronograph.internal import Constants
from chronograph.ui.widgets.song_card import SongCard


@dataclass
class _CoverState:
  token: int = 0
  fut: Optional[Future] = None


@dataclass
class _QueuedCover:
  card: SongCard
  state: _CoverState
  token: int
  mediafile: Path


_COVER_CONCURRENCY = 2
_ACTIVE_COVERS = 0
_COVER_QUEUE: list[_QueuedCover] = []
_COVER_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cover")


def _load_cover_texture(path: Path) -> Optional[Gdk.Texture]:
  try:
    media = parse_file(path)
    return media.get_cover_texture() if media else None
  except Exception:
    return None


# Start queued cover loads while keeping concurrency low for smooth scrolling
def _process_cover_queue() -> None:
  global _ACTIVE_COVERS

  while _ACTIVE_COVERS < _COVER_CONCURRENCY and _COVER_QUEUE:
    req = _COVER_QUEUE.pop(0)

    # List item recycled before starting, drop request
    if req.state.token != req.token:
      continue

    fut = _COVER_POOL.submit(_load_cover_texture, req.mediafile)
    req.state.fut = fut
    _ACTIVE_COVERS += 1

    def done_callback(f: Future, *, req: _QueuedCover = req) -> None:
      def apply() -> bool:
        nonlocal f
        global _ACTIVE_COVERS
        _ACTIVE_COVERS -= 1

        if req.state.token == req.token and req.state.fut is f:
          req.state.fut = None
          try:
            tex: Gdk.Texture = f.result()
          except Exception:
            tex = None

          if tex is not None:
            req.card.set_cover(tex)

        _process_cover_queue()
        return GLib.SOURCE_REMOVE

      GLib.idle_add(apply, priority=GLib.PRIORITY_DEFAULT_IDLE)

    fut.add_done_callback(done_callback)


def _drop_pending_for_state(state: _CoverState) -> None:
  global _COVER_QUEUE
  _COVER_QUEUE = [req for req in _COVER_QUEUE if req.state is not state]


class Library(Gtk.GridView):
  __gtype_name__ = "Library"
  _CARD_WIDTH = 160
  _CARD_GAP = 12
  _MAX_COLUMNS_CAP = 12

  def __init__(self) -> None:
    super().__init__()
    self._adaptive_columns = 0
    self._last_width = 0
    self._bulk_delete_mode = False
    self._bulk_selected_uuids: set[str] = set()
    self._bound_cards: set[SongCard] = set()
    self.add_css_class("library-grid")

    self.cards_model = Gio.ListStore.new(SongCardModel)

    self.card_sort_model = Gtk.SortListModel(model=self.cards_model)
    self.sorter = Gtk.CustomSorter.new(self._cards_sorter_func)
    self.card_sort_model.set_sorter(self.sorter)

    self.card_filter_model = Gtk.FilterListModel(model=self.card_sort_model)
    self.filter = Gtk.CustomFilter.new(self._cards_filter_func)
    self.card_filter_model.set_filter(self.filter)
    self.card_filter_model.connect("notify::n-items", self._on_filter_items)

    self.grid_model = Gtk.NoSelection.new(self.card_filter_model)

    self.grid_factory = Gtk.SignalListItemFactory()
    self.grid_factory.connect("setup", self._on_setup)
    self.grid_factory.connect("bind", self._on_bind)
    self.grid_factory.connect("unbind", self._on_unbind)
    self.grid_factory.connect("teardown", self._on_teardown)

    self.set_model(self.grid_model)
    self.set_factory(self.grid_factory)
    self.set_max_columns(1)
    self.add_tick_callback(self._on_tick_update_columns)

  def _on_setup(self, _factory, list_item: Gtk.ListItem) -> None:
    card = SongCard()
    card._cover_state = _CoverState()  # noqa: SLF001
    list_item.set_child(card)
    list_item.set_focusable(False)
    list_item.set_selectable(False)
    list_item.set_activatable(False)

  def _on_bind(self, _factory, list_item: Gtk.ListItem) -> None:
    card: SongCard = list_item.get_child()
    model: SongCardModel = list_item.get_item()

    st: _CoverState = card._cover_state  # noqa: SLF001
    st.token += 1
    token = st.token

    card.bind(model)
    card.set_bulk_selected(model.uuid in self._bulk_selected_uuids)
    self._bound_cards.add(card)

    card._lyrics_filter_handler = model.connect(  # noqa: SLF001
      "notify::available-lyrics",
      lambda *_: self.filter.changed(Gtk.FilterChange.DIFFERENT),
    )

    if st.fut is not None:
      st.fut.cancel()
      st.fut = None

    _COVER_QUEUE.append(
      _QueuedCover(card=card, state=st, token=token, mediafile=model.mediafile)
    )
    _process_cover_queue()

  def _on_unbind(self, _factory, list_item: Gtk.ListItem) -> None:
    card: SongCard = list_item.get_child()
    if not card:
      return
    model: SongCardModel = list_item.get_item()

    st: _CoverState = card._cover_state  # noqa: SLF001
    if st.fut is not None:
      st.fut.cancel()
      st.fut = None
    _drop_pending_for_state(st)

    card.set_bulk_selected(False)
    card.unbind()
    if model and hasattr(card, "_lyrics_filter_handler"):
      with contextlib.suppress(Exception):
        model.disconnect(card._lyrics_filter_handler)  # noqa: SLF001
      card._lyrics_filter_handler = None  # noqa: SLF001
    self._bound_cards.discard(card)

  def _on_teardown(self, _factory, list_item: Gtk.ListItem) -> None:
    card: SongCard = list_item.get_child()
    if card:
      st: _CoverState = getattr(card, "_cover_state", None)
      if hasattr(card, "_cover_state") and card._cover_state is not None:  # noqa: SLF001
        card._cover_state = None  # noqa: SLF001
      if st and st.fut is not None:
        st.fut.cancel()
        st.fut = None
      card.unbind()
      self._bound_cards.discard(card)
    list_item.set_child(None)

  def _on_tick_update_columns(self, *_args) -> bool:
    width = self.get_allocated_width()
    if width != self._last_width:
      self._last_width = width
      self._update_max_columns(width)
    return GLib.SOURCE_CONTINUE

  def _update_max_columns(self, available_width: int) -> None:
    if available_width <= 0:
      return

    item_width = self._CARD_WIDTH + self._CARD_GAP
    columns = max(1, available_width // item_width)
    columns = min(columns, self._MAX_COLUMNS_CAP)

    if columns != self._adaptive_columns:
      self._adaptive_columns = columns
      self.set_max_columns(columns)

  # TODO: Extend with "Last added" sorting argument
  def _cards_sorter_func(
    self, model1: SongCardModel, model2: SongCardModel, *_args
  ) -> int:
    order = None

    if Constants.WIN.sort_mode == "a-z":
      order = False
    elif Constants.WIN.sort_mode == "z-a":
      order = True

    match Constants.WIN.sort_type:
      case "title":
        return ((model1.title_display > model2.title_display) ^ order) * 2 - 1
      case "artist":
        return ((model1.artist_display > model2.artist_display) ^ order) * 2 - 1
      case "album":
        return ((model1.album_display > model2.album_display) ^ order) * 2 - 1

  def _cards_filter_func(self, model: SongCardModel, *_args) -> bool:
    text = Constants.WIN.search_entry.get_text().lower()
    text_matches = (
      text in model.title_display.lower() or text in model.artist_display.lower()
    )
    tag_filter = Constants.WIN.active_tag_filter
    if tag_filter and tag_filter not in model.tags:
      return False

    flags = model.available_lyrics
    if flags == AvailableLyrics.NONE:
      if not Constants.WIN.filter_none:
        return False
    else:
      allowed = AvailableLyrics.NONE
      if Constants.WIN.filter_plain:
        allowed |= AvailableLyrics.PLAIN
      if Constants.WIN.filter_lrc:
        allowed |= AvailableLyrics.LRC
      if Constants.WIN.filter_elrc:
        allowed |= AvailableLyrics.ELRC
      if not (flags & allowed):
        return False
    return not (text != "" and not text_matches)

  def _on_filter_items(self, *_args) -> None:
    items_filter = self.card_filter_model.get_property("n-items")
    items_all = self.cards_model.get_property("n-items")

    if items_filter == 0 and items_all != 0:
      Constants.WIN.library_stack.set_visible_child(Constants.WIN.empty_filter_results)
    elif items_filter == 0 and items_all == 0:
      Constants.WIN.library_stack.set_visible_child(Constants.WIN.empty_library)
    else:
      Constants.WIN.library_stack.set_visible_child(
        Constants.WIN.library_scrolled_window
      )

  def clear(self) -> None:
    """Remove all cards and reset selection state."""
    self.cards_model.remove_all()
    self._clear_bulk_selection()
    self.card_filter_model.notify("n-items")

  def add_cards(self, cards: list[SongCardModel]) -> None:
    """Append multiple cards to the library.

    Parameters
    ----------
    cards : list[SongCardModel]
      Card models to add.
    """
    for card in cards:
      self.cards_model.append(card)
    self.card_filter_model.notify("n-items")

  def set_bulk_delete_mode(self, enabled: bool) -> None:
    """Enable or disable bulk delete mode.

    Parameters
    ----------
    enabled : bool
      Whether bulk selection mode is active.
    """
    self._bulk_delete_mode = enabled
    if not enabled:
      self._clear_bulk_selection()

  def toggle_bulk_selection(self, card: SongCard, model: SongCardModel) -> None:
    """Toggle selection state for a card in bulk mode.

    Parameters
    ----------
    card : SongCard
      Card widget to update.
    model : SongCardModel
      Model backing the card.
    """
    if not self._bulk_delete_mode:
      return
    track_uuid = model.uuid
    if track_uuid in self._bulk_selected_uuids:
      self._bulk_selected_uuids.remove(track_uuid)
      card.set_bulk_selected(False)
    else:
      self._bulk_selected_uuids.add(track_uuid)
      card.set_bulk_selected(True)

  def _clear_bulk_selection(self) -> None:
    for card in list(self._bound_cards):
      card.set_bulk_selected(False)
    self._bulk_selected_uuids.clear()

  def bulk_delete_selected(self) -> int:
    """Delete all selected cards and return count.

    Returns
    -------
    int
      Number of deleted items.
    """
    if not self._bulk_selected_uuids:
      return 0
    uuids = list(self._bulk_selected_uuids)
    deleted = LibraryManager.delete_files(uuids)

    uuids_set = set(uuids)
    for index in range(self.cards_model.get_n_items() - 1, -1, -1):
      card = self.cards_model.get_item(index)
      if card is not None and card.uuid in uuids_set:
        self.cards_model.remove(index)

    self.card_filter_model.notify("n-items")
    self._clear_bulk_selection()
    return deleted
