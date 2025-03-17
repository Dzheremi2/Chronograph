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
    actions_box: Gtk.Box = Gtk.Template.Child()
    rename_popover: Gtk.Popover = Gtk.Template.Child()

    def __init__(self, path: str, name: str) -> None:
        super().__init__()
        self._path: str = path
        self.title.set_text(name)
        self.set_tooltip_text(path_str + path)

        self.event_controller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_controller_motion)
        self.event_controller_motion.connect("enter", self.toggle_button)
        self.event_controller_motion.connect("leave", self.toggle_button)
        self.rename_popover.set_parent(self)

    @Gtk.Template.Callback()
    def perform_action(self, entry_row: Adw.EntryRow) -> None:
        """Performs rename or delete depends on changed name text

        Parameters
        ----------
        entry_row : Adw.EntryRow
            EntryRow to get text from
        """
        if entry_row.get_text() != "":
            for index, pin in enumerate(shared.cache["pins"]):
                if pin["path"] == self.path:
                    shared.cache["pins"][index]["name"] = entry_row.get_text()
                    self.title.set_text(entry_row.get_text())
                    shared.cache_file.seek(0)
                    shared.cache_file.truncate(0)
                    yaml.dump(
                        shared.cache,
                        shared.cache_file,
                        sort_keys=False,
                        encoding=None,
                        allow_unicode=True,
                    )
                    break
            self.rename_popover.popdown()
        else:
            self.remove_from_saves()
            self.rename_popover.popdown()
            shared.win.add_dir_to_saves_button.set_visible(True)
            shared.win.build_sidebar()
            del self

    def toggle_button(self, *_args) -> None:
        """Chages rename icon visibility"""
        self.actions_box.set_visible(not self.actions_box.get_visible())

    def remove_from_saves(self, *_args) -> None:
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

    @Gtk.Template.Callback()
    def rename_save(self, *_args) -> None:
        """Presents `self.rename_popover`"""
        self.rename_popover.popup()
        self.rename_entry.set_text(self.title.get_text())

    @property
    def path(self) -> str:
        return self._path
