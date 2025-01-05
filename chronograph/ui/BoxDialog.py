from gi.repository import Adw, Gtk  # type: ignore

from chronograph import shared


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/BoxDialog.ui")
class BoxDialog(Adw.Dialog):
    """Dialog with lines of `Adw.ActionRow(s)` with provided content

    Parameters
    ----------
    label : str
        Label of the dialog
    lines_content : tuple
        titles and subtitles of `Adw.ActionRow(s)`. Like `(("1st Title", "1st subtitle"), ("2nd title", "2nd subtitle"), ...)`
    """
    
    __gtype_name__ = "BoxDialog"

    dialog_title_label: Gtk.Label = Gtk.Template.Child()
    props_list: Gtk.ListBox = Gtk.Template.Child()

    def __init__(self, label: str, lines_content: tuple) -> None:
        super().__init__()

        for entry in lines_content:
            self.props_list.append(
                Adw.ActionRow(
                    title=entry[0], subtitle=entry[1], css_classes=["property"], use_markup=False
                )
            )

        self.dialog_title_label.set_label(label)
