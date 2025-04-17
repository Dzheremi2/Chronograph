import yaml
from gi.repository import Adw, Gio, Gtk

from chronograph import shared

path_str: str = _("Path: ")


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/SavedLocation.ui")
class SavedLocation(Gtk.Box):
    """Saved location row for saves sidebar

    Parameters
    ----------
    path : str
        path/to/the/directory
    name : str
        name of the saved location, by default `os.path.basename(path)`
    """

    __gtype_name__ = "SavedLocation"

    title: Gtk.Label = Gtk.Template.Child()
    actions_popover: Gtk.Popover = Gtk.Template.Child()
    rename_dialog: Adw.AlertDialog = Gtk.Template.Child()
    rename_entry: Gtk.Entry = Gtk.Template.Child()
    deletion_alert_dialog: Adw.AlertDialog = Gtk.Template.Child()

    def __init__(self, path: str, name: str) -> None:
        super().__init__()
        self._path: str = path
        self.title.set_text(name)
        self.set_tooltip_text(path_str + path)
        self.actions_popover.set_parent(self)

        self.rmb_gesture = Gtk.GestureClick(button=3)
        self.long_press_gesture = Gtk.GestureLongPress()
        self.add_controller(self.rmb_gesture)
        self.add_controller(self.long_press_gesture)
        self.rmb_gesture.connect("released", lambda *_: self.actions_popover.popup())
        self.long_press_gesture.connect(
            "pressed", lambda *_: self.actions_popover.popup()
        )

        actions: Gio.SimpleActionGroup = Gio.SimpleActionGroup.new()
        rename_action: Gio.SimpleAction = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", self.rename_save)
        delete_action: Gio.SimpleAction = Gio.SimpleAction.new("delete", None)
        delete_action.connect(
            "activate", lambda *_: self.deletion_alert_dialog.present(shared.win)
        )
        actions.add_action(rename_action)
        actions.add_action(delete_action)
        self.insert_action_group("sv", actions)

    @Gtk.Template.Callback()
    def on_deletion_alert_response(
        self, _alert_dialog: Adw.AlertDialog, response: str
    ) -> None:
        if response == "delete":
            self.on_delete_save()

    def on_delete_save(self, *_args) -> None:
        """Removed this saves from `pins` from `shared.cache` and dumps updated cache to file"""
        for index, pin in enumerate(shared.cache["pins"]):
            if pin["path"] == self.path:
                shared.cache["pins"].remove(shared.cache["pins"][index])
                break
        shared.cache_file.seek(0)
        shared.cache_file.truncate(0)
        yaml.dump(
            shared.cache,
            shared.cache_file,
            sort_keys=False,
            encoding=None,
            allow_unicode=True,
        )
        shared.win.build_sidebar(self.path)

    def rename_save(self, *_args) -> None:
        """Presents `self.rename_popover`"""
        self.rename_dialog.present(shared.win)
        self.rename_entry.set_buffer(Gtk.EntryBuffer.new(self.title.get_label(), -1))
        self.rename_entry.grab_focus()

    @Gtk.Template.Callback()
    def on_rename_entry_changed(self, text: Gtk.Text) -> None:
        if text.get_text_length() == 0:
            self.rename_entry.add_css_class("error")
        else:
            if "error" in self.rename_entry.get_css_classes():
                self.rename_entry.remove_css_class("error")

    @Gtk.Template.Callback()
    def do_rename(self, alert_dialog: Adw.AlertDialog, response: str) -> None:
        if response == "rename":
            if alert_dialog.get_extra_child().get_text_length() == 0:
                return
            else:
                for index, pin in enumerate(shared.cache["pins"]):
                    if pin["path"] == self.path:
                        shared.cache["pins"][index]["name"] = (
                            alert_dialog.get_extra_child().get_buffer().get_text()
                        )
                        break
                self.title.set_label(
                    alert_dialog.get_extra_child().get_buffer().get_text()
                )
                shared.cache_file.seek(0)
                shared.cache_file.truncate(0)
                yaml.dump(
                    shared.cache,
                    shared.cache_file,
                    sort_keys=False,
                    encoding=None,
                    allow_unicode=True,
                )
                shared.win.build_sidebar()

    @property
    def path(self) -> str:
        return self._path
