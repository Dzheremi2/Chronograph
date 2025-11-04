from gi.repository import Adw

from chronograph.backend.wbw.models.line_model import LineModel
from chronograph.ui.widgets.wbw.word_widget import WordWidget


class LineWidget(Adw.WrapBox):
  __gtype_name__ = "LineWidget"

  def __init__(self, line: LineModel) -> None:
    super().__init__(
      wrap_policy=Adw.WrapPolicy.NATURAL, child_spacing=5, line_spacing=5
    )

    self.line = line
    for word in self.line:
      self.append(WordWidget(word))
