from typing import Optional

from gi.repository import Gtk

from chronograph.internal import Constants

gtc = Gtk.Template.Child  # pylint: disable=invalid-name

I18N_STRINGS = (
    _("Title"),
    _("Artist"),
    _("Duration"),
    _("Album"),
    _("Is instrumental"),
)

TRUE_STR = _("Yes")
FALSE_STR = _("No")


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/LRClibTrack.ui")
class LRClibTrack(Gtk.Box):
    __gtype_name__ = "LRClibTrack"

    title_label: Gtk.Inscription = gtc()
    artist_label: Gtk.Inscription = gtc()

    def __init__(
        self,
        title: str,
        artist: str,
        tooltip: tuple,
        synced: Optional[str] = "",
        plain: Optional[str] = "",
    ) -> None:
        super().__init__()
        self.title_label.set_text(title)
        self.artist_label.set_text(artist)
        self._synced: str = synced
        self._plain: str = plain
        self.set_tooltip_text(self._generate_tooltip(tooltip))

    def _generate_tooltip(self, tooltip: tuple) -> str:
        tooltip_props = ""
        for i, item in enumerate(tooltip):
            if not isinstance(item, bool):
                string = f"{I18N_STRINGS[i]}: {tooltip[i]}\n"
                tooltip_props += string
            else:
                string = f"{I18N_STRINGS[i]}: {TRUE_STR if item else FALSE_STR}"
                tooltip_props += string
        return tooltip_props

    @property
    def synced(self) -> str:
        return self._synced

    @property
    def plain(self) -> str:
        return self._plain
