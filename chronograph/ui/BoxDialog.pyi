from gi.repository import Adw, Gtk

class BoxDialog(Adw.Dialog):
    """Dialog with lines of `Adw.ActionRow(s)` with provided content

    Parameters
    ----------
    label : str
        Label of the dialog
    lines_content : tuple
        titles and subtitles of `Adw.ActionRow(s)`. Like `(("1st Title", "1st subtitle"), ("2nd title", "2nd subtitle"), ...)`
    """

    dialog_title_label: Gtk.Label
    props_list: Gtk.ListBox
