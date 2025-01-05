from gi.repository import Gtk  # type: ignored

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
    synced : str
        Synced lyrics of track from LRClib, by default `""`
    plain : str
        Plain lyrics of track from LRClib, by default `""`
    """

    title_label: Gtk.Label
    artist_label: Gtk.Label
    synced: str
    plain: str

    def generate_tooltip(self, tuple: tuple) -> str: ...
    def set_lyrics(self, *_args) -> None: ...
