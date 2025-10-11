from gi.repository import Adw, Gtk  # type: ignore

from chronograph.internal import Constants


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/BoxDialog.ui")
class BoxDialog(Adw.Dialog):
  """Dialog with lines of `Adw.ActionRow(s)` with provided content

  Parameters
  ----------
  label : str
      Label of the dialog
  lines_content : tuple[dict]
      tuple of dicts. Each row is a dict with keys::

          "title": str # for row title
          "subtitle": str # for row subtitle
          "action": { # optional for button
              "icon": str # for icon_name button property
              "tooltip": str # for button tooltip
              "callback": Callable # for on click action
          }
  """

  __gtype_name__ = "BoxDialog"

  dialog_title_label: Gtk.Label = Gtk.Template.Child()
  props_list: Gtk.ListBox = Gtk.Template.Child()

  def __init__(self, label: str, lines_content: tuple[dict]) -> None:
    super().__init__()

    for entry in lines_content:
      row = Adw.ActionRow(
        title=entry["title"],
        subtitle=entry["subtitle"],
        css_classes=["property"],
        use_markup=False,
      )

      if "action" in entry.keys() and isinstance(entry["action"], dict):
        action_cfg = entry["action"]
        button = Gtk.Button(
          icon_name=action_cfg["icon"],
          tooltip_text=action_cfg["tooltip"],
          halign=Gtk.Align.CENTER,
          valign=Gtk.Align.CENTER,
        )
        button.connect("clicked", action_cfg["callback"])
        button.add_css_class("flat")
        row.add_suffix(button)

      self.props_list.append(row)

    self.dialog_title_label.set_label(label)
