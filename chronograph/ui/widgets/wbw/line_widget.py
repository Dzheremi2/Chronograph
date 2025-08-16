from gi.repository import Adw

from chronograph.ui.widgets.wbw.word_widget import WordWidget
from chronograph.utils.wbw.models.line_model import LineModel


class LineWidget(Adw.WrapBox):
    __gtype_name__ = "LineWidget"

    def __init__(self, line: LineModel):
        super().__init__(wrap_policy=Adw.WrapPolicy.NATURAL, child_spacing=5, line_spacing=5)
        self.add_css_class("dimmed")

        self.line = line
        for word in self.line:
            self.append(WordWidget(word))
