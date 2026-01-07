from gi.repository import Adw, Gio, Gtk

from chronograph.backend.db.models import Lyric
from chronograph.backend.file.available_lyrics import TEXT_LABELS


class LyricRow(Adw.ActionRow):
  __gtype_name__ = "LyricRow"

  def __init__(self, lyr_uuid: str) -> None:
    self._lyr_uuid = lyr_uuid
    self._lyric: Lyric = Lyric.get_by_id(lyr_uuid)
    fmt = self._lyric.format
    is_finished = self._lyric.finished
    self.set_title(TEXT_LABELS[fmt])

    # Setup prefix
    status_indicator = Gtk.Button(icon_name="chr-check-round-outline-symbolic")
    status_indicator.add_css_class("no-hover")
    status_indicator.add_css_class("flat")

    # Setup suffix
    box = Gtk.Box(valign=Gtk.Align.CENTER, spacing=4)
    import_menu = Gio.Menu()
    import_menu_section = Gio.Menu()
    import_menu_section.append(_("LRClib"), "act1")
    import_menu_section.append(_("Other Lyric"), "act2")
    import_menu.insert_section(0, _("Import From…"), import_menu_section)
    self.import_button = Gtk.MenuButton(
      menu_model=import_menu, icon_name="import-from-symbolic", css_classes=["flat"]
    )
    export_menu = Gio.Menu()
    export_menu_section = Gio.Menu()
    export_menu_section.append("LRClib", "act1")
    export_menu_section.append(_("File"), "act2")
    export_menu_section.append(_("Clipboard"), "act3")
    export_menu.insert_section(0, _("Export To…"), export_menu_section)
    self.export_button = Gtk.MenuButton(
      menu_model=export_menu, icon_name="export-to-symbolic", css_classes=["flat"]
    )
    box.append(self.import_button)
    box.append(self.export_button)

    # Add prefix and suffix
    self.add_suffix(box)
    self.add_prefix(status_indicator)

    if is_finished:
      status_indicator.add_css_class("success")
    else:
      status_indicator.add_css_class("warning")
