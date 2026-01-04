from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from gi.repository import Gdk, Gio, GLib, Gtk

from chronograph.backend.file._song_card_model import SongCardModel
from chronograph.backend.file_parsers import parse_dir, parse_file, parse_files
from chronograph.internal import Constants
from chronograph.ui.widgets._song_card import SongCard


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

  def __init__(self) -> None:
    super().__init__(max_columns=9999999)
    self.list_model = Gio.ListStore.new(SongCardModel)
    self.grid_model = Gtk.NoSelection.new(self.list_model)

    self.grid_factory = Gtk.SignalListItemFactory()
    self.grid_factory.connect("setup", self._on_setup)
    self.grid_factory.connect("bind", self._on_bind)
    self.grid_factory.connect("unbind", self._on_unbind)
    self.grid_factory.connect("teardown", self._on_teardown)

    self.set_model(self.grid_model)
    self.set_factory(self.grid_factory)

    for file in parse_files(parse_dir("/home/dzheremi/Music/LRCLIB") * 10):
      self.list_model.append(SongCardModel(Path(file.path), Path(file.path).name))

  def _on_setup(self, _factory, list_item: Gtk.ListItem) -> None:
    card = SongCard()
    card._cover_state = _CoverState()  # noqa: SLF001
    list_item.set_child(card)

  def _on_bind(self, _factory, list_item: Gtk.ListItem) -> None:
    card: SongCard = list_item.get_child()
    model: SongCardModel = list_item.get_item()

    st: _CoverState = card._cover_state  # noqa: SLF001
    st.token += 1
    token = st.token

    card.set_cover(None)
    card.bind(model)

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

    card.cover_img.set_from_paintable(Constants.COVER_PLACEHOLDER)

    st: _CoverState = card._cover_state  # noqa: SLF001
    if st.fut is not None:
      st.fut.cancel()
      st.fut = None
    _drop_pending_for_state(st)

    card.unbind()

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
    list_item.set_child(None)
