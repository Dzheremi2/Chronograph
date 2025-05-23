from gi.repository import Adw, Gio, Gtk  # type: ignore

from chronograph import shared


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/ui/Preferences.ui")
class ChronographPreferences(Adw.PreferencesDialog):
    """Preferences dialog"""

    __gtype_name__ = "ChronographPreferences"

    reset_quick_edit_switch: Adw.SwitchRow = Gtk.Template.Child()
    auto_file_manipulation_switch: Adw.ExpanderRow = Gtk.Template.Child()
    auto_file_manipulation_format: Adw.ComboRow = Gtk.Template.Child()
    save_session_on_quit_switch: Adw.SwitchRow = Gtk.Template.Child()
    precise_milliseconds_switch: Adw.SwitchRow = Gtk.Template.Child()
    automatic_list_view_switch: Adw.SwitchRow = Gtk.Template.Child()
    recursive_parsing_switch: Adw.ExpanderRow = Gtk.Template.Child()
    follow_symlinks_switch: Adw.SwitchRow = Gtk.Template.Child()
    load_compressed_covers_switch: Adw.ExpanderRow = Gtk.Template.Child()
    compress_level_spin: Adw.SpinRow = Gtk.Template.Child()
    compress_level_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    opened = False

    def __init__(self) -> None:
        super().__init__()
        self.__class__.opened = True
        self.connect("closed", lambda *_: self.set_opened(False))
        self.auto_file_manipulation_format.connect(
            "notify::selected", self.update_auto_file_format_schema
        )
        self.automatic_list_view_switch.connect("notify::active", self.set_view_switcher_inactive)
        shared.schema.bind(
            "auto-file-manipulation",
            self.auto_file_manipulation_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "reset-quick-editor",
            self.reset_quick_edit_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "save-session",
            self.save_session_on_quit_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "precise-milliseconds",
            self.precise_milliseconds_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "auto-list-view",
            self.automatic_list_view_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "recursive-parsing",
            self.recursive_parsing_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "follow-symlinks",
            self.follow_symlinks_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "load-compressed-covers",
            self.load_compressed_covers_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )
        shared.schema.bind(
            "compress-level",
            self.compress_level_adjustment,
            "value",
            Gio.SettingsBindFlags.DEFAULT,
        )

        if shared.schema.get_string("auto-file-format") == ".lrc":
            self.auto_file_manipulation_format.set_selected(0)
        elif shared.schema.get_string("auto-file-format") == ".txt":
            self.auto_file_manipulation_format.set_selected(1)

    def update_auto_file_format_schema(self, *_args) -> None:
        """Updates `shared.schema` with new preferred file format"""
        selected = self.auto_file_manipulation_format.get_selected()
        if selected == 0:
            shared.schema.set_string("auto-file-format", ".lrc")
        elif selected == 1:
            shared.schema.set_string("auto-file-format", ".txt")

    def set_view_switcher_inactive(self, *_args) -> None:
        if self.automatic_list_view_switch.get_active():
            shared.app.lookup_action("view_type").set_enabled(False)
        else:
            shared.app.lookup_action("view_type").set_enabled(True)

    def set_opened(self, opened: bool) -> None:
        """Controls possibility to open `self` only once at the time

        Parameters
        ----------
        opened : bool
            new `opened` value
        """
        self.__class__.opened = opened
