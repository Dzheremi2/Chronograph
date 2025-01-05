from typing import Union

from gi.repository import Adw, Gtk

from chronograph import shared

i18n_strings = (
    title_str := _("Title"),
    artist_str := _("Artist"),
    duration_str := _("Duration"),
    album_str := _("Album"),
    instrumental_str := _("Is instrumental"),
)

true_str = _("Yes")
false_str = _("No")


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/LrclibTrack.ui")
class LrclibTrack(Gtk.Box):
    """Returns new `LrclibTrack` with provided data (all data are required)

    Parameters
    ----------
    tooltip : tuple
        Tuple with Title, Artist, Duration, Album, and IsInstrumental properties of track
    ::

        tuple("title", "artist", 130, "album", True)

    title : str
        Title of track from LRClib
    artist : str
        Artist of track from LRClib
    synced : str | None
        Synced lyrics of track from LRClib, by default `""`
    plain : str | None
        Plain lyrics of track from LRClib, by default `""`
    """

    title_label: Gtk.Inscription = Gtk.Template.Child()
    artist_label: Gtk.Inscription = Gtk.Template.Child()

    __gtype_name__ = "LrclibTrack"

    def __init__(
        self,
        title: str,
        artist: str,
        tooltip: tuple,
        synced: Union[str, None] = "",
        plain: Union[str, None] = "",
    ):
        super().__init__()
        self.title_label.set_text(title)
        self.artist_label.set_text(artist)
        self.synced: str = synced
        self.plain: str = plain
        self.set_tooltip_text(self.generate_tooltip(tooltip))

    def generate_tooltip(self, tuple: tuple) -> str:
        """Generated tooltip with Title, Artist, Duration, Album and IsInstrumental

        Parameters
        ----------
        tuple : tuple
            Tuple with Title, Artist, Duration, Album, and IsInstrumental properties of track
        ::

            tuple("title", "artist", 130, "album", True)

        Returns
        -------
        str
            Prepared tooltip string for setting using `self.set_tooltip_text()` function
        """
        tooltip_props = ""
        for i in range(len(tuple)):
            if type(tuple[i]) is not bool:
                string = f"{i18n_strings[i]}: {tuple[i]}\n"
                tooltip_props += string
            else:
                string = f"{i18n_strings[i]}: {true_str if tuple[i] else false_str}"
                tooltip_props += string
        return tooltip_props

    def set_lyrics(self, *_args) -> None:
        """Sets lyrics parsed from LRClib to respective `Gtk.TextView` in `chronograph.ChronographWindow.lrclib_window`"""
        if (
            shared.win.lrclib_window_main_clamp.get_child()
            is shared.win.lrclib_window_collapsed_navigation_view
        ):
            shared.win.lrclib_window_collapsed_navigation_view.push(
                shared.win.lrclib_window_collapsed_lyrics_page
            )
        if self.synced is not None:
            shared.win.lrclib_window_synced_lyrics_text_view.set_buffer(
                Gtk.TextBuffer(text=self.synced)
            )
        else:
            shared.win.lrclib_window_synced_lyrics_text_view.set_buffer(
                Gtk.TextBuffer.new()
            )
            shared.win.lrclib_window_toast_overlay.add_toast(
                Adw.Toast(title=_("No synced lyrics available"))
            )

        if self.plain is not None:
            shared.win.lrclib_window_plain_lyrics_text_view.set_buffer(
                Gtk.TextBuffer(text=self.plain)
            )
        else:
            shared.win.lrclib_window_plain_lyrics_text_view.set_buffer(
                Gtk.TextBuffer.new()
            )
            shared.win.lrclib_window_toast_overlay.add_toast(
                Adw.Toast(title=_("No plain lyrics available"))
            )
