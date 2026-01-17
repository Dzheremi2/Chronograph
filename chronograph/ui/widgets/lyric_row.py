from gi.repository import Adw, Gio, Gtk

from chronograph.backend.file.available_lyrics import TEXT_LABELS


# TODO: Implement export actions
class LyricRow(Adw.ActionRow):
  __gtype_name__ = "LyricRow"

  def __init__(self, fmt: str, available: bool = True) -> None:
    super().__init__()
    fmt_key = fmt.lower()
    self.set_title(TEXT_LABELS.get(fmt_key, fmt.upper()))

    # Setup prefix
    status_indicator = Gtk.Button(
      icon_name="chr-check-round-outline-symbolic", focusable=False
    )
    status_indicator.add_css_class("no-hover")
    status_indicator.add_css_class("flat")

    # Setup suffix
    box = Gtk.Box(valign=Gtk.Align.CENTER, spacing=4)
    export_menu = Gio.Menu()
    export_menu_section = Gio.Menu()
    export_menu_section.append("LRClib", "act1")
    export_menu_section.append(_("File"), "act2")
    export_menu_section.append(_("Clipboard"), "act3")
    export_menu.insert_section(0, _("TBI Export To…"), export_menu_section)
    export_button = Gtk.MenuButton(
      menu_model=export_menu, icon_name="export-to-symbolic", css_classes=["flat"]
    )
    box.append(export_button)

    # Add prefix and suffix
    self.add_suffix(box)
    self.add_prefix(status_indicator)

    if available:
      status_indicator.add_css_class("success")
    else:
      status_indicator.add_css_class("warning")
