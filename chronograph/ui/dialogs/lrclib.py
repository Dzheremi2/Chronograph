import threading

import requests
from gi.repository import Adw, Gio, GLib, Gtk

from chronograph.internal import Constants
from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncPage
from chronograph.ui.sync_pages.wbw_sync_page import WBWSyncPage
from chronograph.ui.widgets.lrclib_track import LRClibTrack
from dgutils.actions import Actions

gtc = Gtk.Template.Child  # pylint: disable=invalid-name
logger = Constants.LOGGER
lrclib_logger = Constants.LRCLIB_LOGGER


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/LRClib.ui")
@Actions.from_schema(Constants.PREFIX + "/resources/actions/lrclib.yaml")
class LRClib(Adw.Dialog):
  __gtype_name__ = "LRClib"

  nothing_found_status_page: Adw.StatusPage = gtc()
  search_lrclib_status_page: Adw.StatusPage = gtc()

  toast_overlay: Adw.ToastOverlay = gtc()
  nav_view: Adw.NavigationView = gtc()
  main_box: Gtk.Box = gtc()
  title_entry: Gtk.Entry = gtc()
  artist_entry: Gtk.Entry = gtc()
  album_entry: Gtk.Entry = gtc()
  search_button: Gtk.Button = gtc()
  lrctracks_scrolled_window: Gtk.ScrolledWindow = gtc()
  lrctracks_list_box: Gtk.ListBox = gtc()
  lyrics_box: Gtk.Box = gtc()

  synced_text_view: Gtk.TextView = gtc()
  plain_text_view: Gtk.TextView = gtc()

  collapsed_lyrics_nav_page: Adw.NavigationPage = gtc()
  collapsed_bin: Adw.Bin = gtc()

  def __init__(self, title: str = "", artist: str = "", album: str = "") -> None:
    super().__init__()

    self.lrctracks_list_box.set_placeholder(self.search_lrclib_status_page)
    self.title_entry.set_text(title)
    self.artist_entry.set_text(artist)
    self.album_entry.set_text(album)

    self._on_title_entry_changed(self.title_entry)

  @Gtk.Template.Callback()
  def _on_title_entry_changed(self, entry: Gtk.Entry) -> None:
    if len(entry.get_text()) == 0:
      entry.add_css_class("error")
      self.search_button.set_sensitive(False)
    else:
      entry.remove_css_class("error")
      self.search_button.set_sensitive(True)

  def _search(self, *_args) -> None:
    def on_search_result(rq_result: list) -> None:
      self.lrctracks_list_box.remove_all()
      if len(rq_result) > 0:
        self.lrctracks_list_box.remove_all()
        for item in rq_result:
          logger.debug(
            "Adding '%s -- %s / %s' to result list",
            item["trackName"],
            item["artistName"],
            item["albumName"],
          )
          self.lrctracks_list_box.append(
            LRClibTrack(
              title=item["trackName"],
              artist=item["artistName"],
              tooltip=(
                item["trackName"],
                item["artistName"],
                item["duration"],
                item["albumName"],
                item["instrumental"],
              ),
              synced=item["syncedLyrics"],
              plain=item["plainLyrics"],
            )
          )
        self.lrctracks_scrolled_window.set_child(self.lrctracks_list_box)
      else:
        self.lrctracks_scrolled_window.set_child(self.nothing_found_status_page)

    def on_search_error(title: str, desc: str, icon: str) -> None:
      self.lrctracks_scrolled_window.set_child(
        Adw.StatusPage(
          title=title,
          description=desc,
          icon_name=icon,
        )
      )

    def do_request() -> None:
      self.search_button.set_sensitive(False)
      _err = None
      try:
        lrclib_logger.info("Connecting to lrclib.net")
        request: requests.Response = requests.get(
          url="https://lrclib.net/api/search",
          params={
            "track_name": self.title_entry.get_text().strip(),
            "artist_name": self.artist_entry.get_text().strip(),
            "album_name": self.album_entry.get_text().strip(),
          },
          timeout=10,
        )
        lrclib_logger.info("Established connection to lrclib.net")
        rq_result = request.json()
        GLib.idle_add(on_search_result, rq_result)
      except requests.exceptions.ConnectionError as e:
        GLib.idle_add(
          on_search_error,
          _("Connection Error"),
          _(
            "Failed to connect to the LRC library server. Please check your internet connection and try again"
          ),
          "chr-no-internet-connection-symbolic",
        )
        _err = e
        return
      except requests.exceptions.Timeout as e:
        GLib.idle_add(
          on_search_error,
          _("Timeout Error"),
          _("The request to the LRC library server timed out. Please try again later"),
          "chr-connection-timeout-symbolic",
        )
        _err = e
        return
      except Exception as e:
        GLib.idle_add(
          on_search_error,
          _("Something went wrong"),
          _(
            "An unknown error occurred while trying to connect to the LRC library server"
          ),
          "chr-error-occured-symbolic.svg",
        )
        _err = e
        return
      finally:
        self.search_button.set_sensitive(True)
        if _err:
          lrclib_logger.warning(
            "Unable to fetch available lyrics for {title: %s, artist: %s}: %s",
            self.title_entry.get_text().strip(),
            self.artist_entry.get_text().strip(),
            _err,
            stack_info=True,
          )

    threading.Thread(target=do_request, daemon=True).start()

  def _import_synced(self, *_args) -> None:
    from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncLine

    if text := self.synced_text_view.get_buffer().get_text(
      self.synced_text_view.get_buffer().get_start_iter(),
      self.synced_text_view.get_buffer().get_end_iter(),
      False,
    ):
      if isinstance(
        (page := Constants.WIN.navigation_view.get_visible_page()), LRCSyncPage
      ):
        page.sync_lines.remove_all()
        for _, line in enumerate(text.splitlines()):
          page.sync_lines.append(LRCSyncLine(line))
      elif isinstance(
        (page := Constants.WIN.navigation_view.get_visible_page()), WBWSyncPage
      ):
        buffer = Gtk.TextBuffer()
        buffer.set_text(text)
        page.edit_view_text_view.set_buffer(buffer)
      self.close()
      logger.debug("Imported synced lyrics")

  def _import_plain(self, *_args) -> None:
    from chronograph.ui.sync_pages.lrc_sync_page import LRCSyncLine

    if text := self.plain_text_view.get_buffer().get_text(
      self.plain_text_view.get_buffer().get_start_iter(),
      self.plain_text_view.get_buffer().get_end_iter(),
      False,
    ):
      if isinstance(
        (page := Constants.WIN.navigation_view.get_visible_page()), LRCSyncPage
      ):
        page: LRCSyncPage
        page.sync_lines.remove_all()
        for _, line in enumerate(text.splitlines()):
          page.sync_lines.append(LRCSyncLine(line))
      elif isinstance(
        (page := Constants.WIN.navigation_view.get_visible_page()), WBWSyncPage
      ):
        page: WBWSyncPage
        buffer = Gtk.TextBuffer()
        buffer.set_text(text)
        page.edit_view_text_view.set_buffer(buffer)
      self.close()
      logger.debug("Imported plain lyrics")

  @Gtk.Template.Callback()
  def on_breakpoint(self, *_args) -> None:
    """Handles the breakpoint action to toggle the visibility of the lyrics box"""
    if self.collapsed_bin.get_child() != self.lyrics_box:
      self.main_box.remove(self.lyrics_box)
      self.collapsed_bin.set_child(self.lyrics_box)
    else:
      self.collapsed_bin.set_child(None)
      self.main_box.append(self.lyrics_box)

  @Gtk.Template.Callback()
  def on_track_load(self, _listbox, row: Gtk.ListBoxRow) -> None:
    """Loads lyrics from selected track into the text views

    Parameters
    ----------
    _listbox : Gtk.ListBox
        A Gtk.ListBox containing the tracks
    row : Gtk.ListBoxRow
        A Gtk.ListBoxRow containing the selected track
    """
    synced: str = row.get_child().synced
    plain: str = row.get_child().plain
    if synced:
      self.synced_text_view.set_buffer(Gtk.TextBuffer(text=synced))
    else:
      self.synced_text_view.set_buffer(Gtk.TextBuffer())
      self.toast_overlay.add_toast(Adw.Toast.new(_("No synced lyrics available")))
    if plain:
      self.plain_text_view.set_buffer(Gtk.TextBuffer(text=plain))
    else:
      self.plain_text_view.set_buffer(Gtk.TextBuffer())
      self.toast_overlay.add_toast(Adw.Toast.new(_("No plain lyrics available")))

    if self.collapsed_bin.get_child() == self.lyrics_box:
      self.nav_view.push(self.collapsed_lyrics_nav_page)
    logger.debug(
      "Lyrics for \n----------\n%s\n----------\nwere loaded to TextViews",
      row.get_child().get_tooltip_text(),
    )
