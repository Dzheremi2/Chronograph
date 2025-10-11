from typing import Iterator, Optional

from gi.repository import Gio, GObject

from chronograph.utils.wbw.models.word_model import WordModel
from chronograph.utils.wbw.token_parser import TokenParser
from chronograph.utils.wbw.tokens import LineToken


class LineModel(GObject.Object):
  """Model representing a line of lyrics."""

  __gtype_name__ = "LineModel"

  __gsignals__ = {
    "cindex-changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    "end-of-line": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
  }

  text: str = GObject.Property(type=str, default="")
  line: str = GObject.Property(type=str, default="")
  time: int = GObject.Property(type=int, default=-1)
  timestamp = GObject.Property(type=str, default="")
  cindex: int = GObject.Property(type=int, default=-1)
  words: Gio.ListStore = GObject.Property(type=Gio.ListStore)

  def __init__(self, line: LineToken) -> None:
    """Create model from `LineToken`"""
    from chronograph.ui.widgets.wbw.line_widget import LineWidget

    try:
      ms = int(line)
    except TypeError:
      ms = -1

    super().__init__(
      text=line.text,
      line=line.line,
      time=ms,
      timestamp=line.timestamp or "",
    )

    store: Gio.ListStore = Gio.ListStore.new(item_type=WordModel)
    for word in TokenParser.parse_words(line):
      model = WordModel(word)
      store.append(model)
    self.set_property("words", store)

    self.widget = LineWidget(self)

  def set_current(self, index: int) -> None:
    """Set the current highlighted word index.

    Parameters
    ----------
    index : int
        Index of the word to be highlighted
    """
    if index == self.cindex:
      return

    if 0 <= index < self.words.get_n_items():
      old = self.cindex
      self.set_property("cindex", index)
      self.emit("cindex-changed", old, index)
      for word in self:
        word.set_property("highlighted", False)
      self.words.get_item(self.cindex).set_property("highlighted", True)
    else:
      # pylint: disable=superfluous-parens
      self.emit("end-of-line", not (index < 0))
      self.cindex = -1
      for word in self:
        word.set_property("highlighted", False)

  def next(self) -> None:
    """Advance to the next word."""
    self.set_current(self.cindex + 1)

  def previous(self) -> None:
    """Move to the previous word."""
    self.set_current(self.cindex - 1)

  def set_is_current_line(self, is_current_line: bool) -> None:
    """Applied to all words to mark them as "in current line" or not.

    Parameters
    ----------
    in_current_line : bool
        True if this line is current, False otherwise
    """
    for word in self:
      word.set_property("active", is_current_line)

    if is_current_line:
      if self.cindex == -1 and self.words.get_n_items() > 0:
        self.set_current(0)
    else:
      if self.cindex != -1:
        self.set_current(-1)

  def get_latest_unsynced(self) -> Optional[tuple[WordModel, int]]:
    """Returns the last word and its index if not all words were synchronized. `None` if all words are synced

    Returns
    -------
    Optional[tuple[WordModel, int]]
    """

    for word in self:
      if word.time == -1:
        return word, self.words.find(word)[1]
    return None

  def get_current_word(self) -> WordModel:
    """Return the currently highlighted word."""
    return self[self.cindex]

  def restore_token(self) -> LineToken:
    """Recreate `LineToken` from the model."""
    return LineToken(self.text, self.line, time=self.time, timestamp=self.timestamp)

  def __iter__(self) -> Iterator[WordModel]:
    """Iterate through all words in the line."""
    for i in range(self.words.get_n_items()):
      yield self.words.get_item(i)

  def __getitem__(self, index) -> WordModel:
    """Return word by index."""
    try:
      if (item := self.words.get_item(index)) is not None:
        return item
      raise IndexError("List index out of range")
    except (IndexError, OverflowError) as e:
      raise IndexError("List index out of range") from e
