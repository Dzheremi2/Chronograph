import yaml
from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.internal import Constants, Schema

gtc = Gtk.Template.Child  # pylint: disable=invalid-name
logger = Constants.LOGGER


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/SavedLocation.ui")
class SavedLocation(Gtk.Box):
  __gtype_name__ = "SavedLocation"

  title: Gtk.Label = gtc()
  actions_popover: Gtk.Popover = gtc()
  rename_dialog: Adw.AlertDialog = gtc()
  rename_entry: Gtk.Entry = gtc()
  deletion_alert_dialog: Adw.AlertDialog = gtc()

  def __init__(self, path: str, name: str) -> None:
    super().__init__()
    self._path = path
    self._name = name
    self.bind_property("name", self.title, "label", GObject.BindingFlags.SYNC_CREATE)
    # pylint: disable=not-callable
    self.set_tooltip_text(_("Path: {}").format(self.path))
    self.connect(
      "notify::path",
      # Translators: Do not translate the curly braces, they are used for formatting
      lambda *_: self.set_tooltip_text(_("Path: {}").format(self.path)),
    )
    self.actions_popover.set_parent(self)

    self.rmb_gesture = Gtk.GestureClick(button=3)
    self.long_press_gesture = Gtk.GestureLongPress()
    self.add_controller(self.rmb_gesture)
    self.add_controller(self.long_press_gesture)
    self.rmb_gesture.connect("released", lambda *_: self.actions_popover.popup())
    self.long_press_gesture.connect("pressed", lambda *_: self.actions_popover.popup())

    actions: Gio.SimpleActionGroup = Gio.SimpleActionGroup.new()
    rename_action: Gio.SimpleAction = Gio.SimpleAction.new("rename", None)
    rename_action.connect("activate", self.rename_save)
    delete_action: Gio.SimpleAction = Gio.SimpleAction.new("delete", None)
    delete_action.connect(
      "activate", lambda *_: self.deletion_alert_dialog.present(Constants.WIN)
    )
    actions.add_action(rename_action)
    actions.add_action(delete_action)
    self.insert_action_group("sv", actions)

  def load(self) -> None:
    """Loads the saved location"""
    if self.path != Schema.get("root.state.library.session"):
      Constants.WIN.open_directory(self.path)
      Constants.WIN.sidebar.select_row(self.get_parent())

  @Gtk.Template.Callback()
  def on_deletion_alert_response(
    self, _alert_dialog: Adw.AlertDialog, response: str
  ) -> None:
    if response == "delete":
      self.on_delete_save()

  def on_delete_save(self) -> None:
    """Deletes the saved location"""
    for index, pin in enumerate(Constants.CACHE["pins"]):
      if pin["path"] == self.path:
        Constants.CACHE["pins"].remove(Constants.CACHE["pins"][index])
        break
    Constants.CACHE_FILE.seek(0)
    Constants.CACHE_FILE.truncate(0)
    yaml.dump(
      Constants.CACHE,
      Constants.CACHE_FILE,
      allow_unicode=True,
      sort_keys=False,
      encoding=None,
    )
    logger.info("'%s' was removed from saves", self.name)
    Constants.WIN.build_sidebar()

  def rename_save(self, *_args) -> None:
    """Presents `self.rename_popover`"""
    self.rename_dialog.present(Constants.WIN)
    self.rename_entry.set_buffer(Gtk.EntryBuffer.new(self.title.get_label(), -1))
    self.rename_entry.grab_focus()

  @Gtk.Template.Callback()
  def on_rename_entry_changed(self, text: Gtk.Text) -> None:
    """Checks if the rename entry is empty and adds an error class if it is

    Parameters
    ----------
    text : Gtk.Text
        The text entry that is used to rename the save
    """
    if text.get_text_length() == 0:
      self.rename_entry.add_css_class("error")
    else:
      if "error" in self.rename_entry.get_css_classes():
        self.rename_entry.remove_css_class("error")

  @Gtk.Template.Callback()
  def do_rename(self, alert_dialog: Adw.AlertDialog, response: str) -> None:
    """Renames the save in `shared.cache` and dumps updated cache to file

    Parameters
    ----------
    alert_dialog : Adw.AlertDialog
        An alert dialog that is used to rename the save
    response : str
        The response of the alert dialog
    """
    if response == "rename":
      if alert_dialog.get_extra_child().get_text_length() == 0:
        return
      for index, pin in enumerate(Constants.CACHE["pins"]):
        if pin["path"] == self.path:
          Constants.CACHE["pins"][index]["name"] = (
            alert_dialog.get_extra_child().get_buffer().get_text()
          )
          break
      logger.info(
        "'%s' was renamed to '%s'",
        self.name,
        alert_dialog.get_extra_child().get_buffer().get_text(),
      )
      self.title.set_label(alert_dialog.get_extra_child().get_buffer().get_text())
      Constants.CACHE_FILE.seek(0)
      Constants.CACHE_FILE.truncate(0)
      yaml.dump(
        Constants.CACHE,
        Constants.CACHE_FILE,
        sort_keys=False,
        encoding=None,
        allow_unicode=True,
      )
      Constants.WIN.build_sidebar()

  ############### Notifiable Properties ###############
  @GObject.Property(type=str, default="")
  def name(self) -> str:
    """Title of the saved location"""
    return self._name

  @name.setter
  def name(self, value: str) -> None:
    self._name = value

  @GObject.Property(type=str, default="")
  def path(self) -> str:
    """Path of the saved location"""
    return self._path

  @path.setter
  def path(self, value: str) -> None:
    self._path = value
