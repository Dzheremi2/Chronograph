from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.backend.asynchronous.async_task import AsyncTask
from chronograph.backend.file.library_model import LibraryModel
from chronograph.backend.lrclib.lrclib_service import FetchStates, LRClibService
from chronograph.backend.media import BaseFile  # noqa: TC001
from chronograph.internal import Constants

gtc = Gtk.Template.Child


@Gtk.Template(
  resource_path=Constants.PREFIX + "/gtk/ui/dialogs/MassDownloadingDialog.ui"
)
class MassDownloadingDialog(Adw.Dialog):
  __gtype_name__ = "MassDownloadingDialog"

  fetch_log_list_box: Gtk.ListBox = gtc()
  no_log_yet: Adw.StatusPage = gtc()

  log_items: Gio.ListStore = GObject.Property(type=Gio.ListStore)

  _fetch_going = False

  def __init__(self) -> None:
    super().__init__()
    self.fetch_log_list_box.set_placeholder(self.no_log_yet)
    store = Gio.ListStore.new(item_type=LogEntry)
    self.set_property("log_items", store)
    self.fetch_log_list_box.bind_model(self.log_items, self._log_row_factory)

  @Gtk.Template.Callback()
  def _on_fetch_button_clicked(self, button: Gtk.Button) -> None:
    def on_all_done(*_args) -> None:
      self._fetch_going = False
      button.set_label(_("Fetch"))

    if not self._fetch_going:
      if self.log_items.get_n_items() != 0:
        self.log_items.remove_all()
        # FIXME: Create a class (in dgutils) wrapper for Handlers to provide an API
        # methods "disconnect_all" to kill all handlers
        LRClibService().disconnect(self.fstr)
        LRClibService().disconnect(self.fmsg)
        LRClibService().disconnect(self.fst)
        LRClibService().disconnect(self.fad)
      medias: list[BaseFile] = []
      for item in LibraryModel().library:
        media = item.get_child().model.mfile
        medias.append(media)
      self.task = AsyncTask(
        LRClibService().fetch_lyrics_many,
        medias,
        do_use_progress=True,
        do_use_cancellable=True,
      )
      self.task.start()
      self._fetch_going = True
      self.fstr = LRClibService().connect(
        "fetch-started", lambda _lrclib, path: self.log_items.append(LogEntry(path))
      )
      self.fmsg = LRClibService().connect("fetch-message", self._on_fetch_message)
      self.fst = LRClibService().connect("fetch-state", self._on_fetch_state)
      button.set_label(_("Cancel"))
      self.fad = LRClibService().connect("fetch-all-done", on_all_done)
    else:
      self.task.cancel()

  def _on_fetch_state(self, _lrclib, path: str, state: FetchStates) -> None:
    for item in self.log_items:
      if item.path == path:
        # fmt: off
        match state:
          case FetchStates.DONE: item.props.done = True
          case FetchStates.FAILED: item.props.failed = True
          case FetchStates.CANCELLED: item.props.cancelled = True
        # fmt: on
        break

  def _on_fetch_message(self, _lrclib, path: str, message: str) -> None:
    for item in self.log_items:
      if item.path == path:
        item.set_property("message", message)
        break

  def _log_row_factory(self, item: "LogEntry") -> Adw.ActionRow:
    row = Adw.ActionRow(title=item.path, subtitle=item.message, use_markup=False)
    item.bind_property("message", row, "subtitle")
    prefix = Adw.Bin()
    spinner = Adw.Spinner()
    failed_icon = Gtk.Image(
      icon_name="chr-exclamation-mark-symbolic", css_classes=["error"]
    )
    done_icon = Gtk.Image(
      icon_name="chr-check-round-outline-symbolic", css_classes=["success"]
    )
    cancelled_icon = Gtk.Image(
      icon_name="nothing-found-symbolic", css_classes=["warning"]
    )
    prefix.set_child(spinner)
    row.add_prefix(prefix)
    item.connect("notify::failed", lambda *__: prefix.set_child(failed_icon))
    item.connect("notify::done", lambda *__: prefix.set_child(done_icon))
    item.connect("notify::cancelled", lambda *__: prefix.set_child(cancelled_icon))
    return row


class LogEntry(GObject.Object):
  message: str = GObject.Property(type=str, default="")
  failed: bool = GObject.Property(type=bool, default=False)
  done: bool = GObject.Property(type=bool, default=False)
  cancelled: bool = GObject.Property(type=bool, default=False)

  def __init__(self, path: str, message: str = _("Pending")) -> None:
    super().__init__(message=message)
    self.path = path
