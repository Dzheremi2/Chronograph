from gi.repository import Adw, GObject, Gtk

from chronograph.internal import Constants, Schema
from chronograph.utils.parsers import parse_dir

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/SavedLocation.ui")
class SavedLocation(Gtk.Box):
    __gtype_name__ = "SavedLocation"

    title: Gtk.Label = gtc()
    actions_popover: Gtk.Popover = gtc()
    rename_dialog: Adw.AlertDialog = gtc()
    rename_entry: Gtk.Entry = gtc()
    deletion_alert_dialog: Adw.AlertDialog = gtc()

    def __init__(self, path: str, name: str) -> "SavedLocation":
        super().__init__()
        self._path = path
        self._name = name
        self.bind_property(
            "name", self.title, "label", GObject.BindingFlags.SYNC_CREATE
        )
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
        self.long_press_gesture.connect(
            "pressed", lambda *_: self.actions_popover.popup()
        )

        # actions: Gio.SimpleActionGroup = Gio.SimpleActionGroup.new()
        # rename_action: Gio.SimpleAction = Gio.SimpleAction.new("rename", None)
        # rename_action.connect("activate", self.rename_save)
        # delete_action: Gio.SimpleAction = Gio.SimpleAction.new("delete", None)
        # delete_action.connect(
        #     "activate", lambda *_: self.deletion_alert_dialog.present(Constants.WIN)
        # )
        # actions.add_action(rename_action)
        # actions.add_action(delete_action)
        # self.insert_action_group("sv", actions)

    def load(self) -> None:
        """Loads the saved location"""
        # pylint: disable=import-outside-toplevel
        from chronograph.window import WindowState

        if self.path != Schema.session:
            Constants.WIN.open_directory(self.path)
            Constants.WIN.sidebar.select_row(self.get_parent())
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
