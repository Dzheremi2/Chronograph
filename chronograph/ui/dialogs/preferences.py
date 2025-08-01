from gi.repository import Adw, Gio, Gtk

from chronograph.internal import Constants, Schema

gtc = Gtk.Template.Child  # pylint: disable=invalid-name


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/Preferences.ui")
class ChronographPreferences(Adw.PreferencesDialog):
    __gtype_name__ = "ChronographPreferences"

    reset_quick_edit_switch: Adw.SwitchRow = gtc()
    auto_file_manipulation_switch: Adw.ExpanderRow = gtc()
    auto_file_manipulation_format: Adw.ComboRow = gtc()
    autosave_throttling_adjustment: Gtk.Adjustment = gtc()
    save_session_on_quit_switch: Adw.SwitchRow = gtc()
    precise_milliseconds_switch: Adw.SwitchRow = gtc()
    automatic_list_view_switch: Adw.SwitchRow = gtc()
    recursive_parsing_switch: Adw.ExpanderRow = gtc()
    follow_symlinks_switch: Adw.SwitchRow = gtc()
    load_compressed_covers_switch: Adw.ExpanderRow = gtc()
    compress_level_spin: Adw.SpinRow = gtc()
    compress_level_adjustment: Gtk.Adjustment = gtc()
    enable_debug_logging_switch: Adw.SwitchRow = gtc()

    opened: bool = False

    def __init__(self) -> "ChronographPreferences":
        super().__init__()

        self.__class__.opened = True
        self.connect("closed", lambda *_: self._set_opened(False))
        self.auto_file_manipulation_format.connect(
            "notify::selected", self._update_auto_file_format_schema
        )
        self.automatic_list_view_switch.connect(
            "notify::active", self._set_view_switcher_inactive
        )

        Schema.bind(
            "STATELESS",
            "auto-file-manipulation",
            self.auto_file_manipulation_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "reset-quick-editor",
            self.reset_quick_edit_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "save-session",
            self.save_session_on_quit_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "precise-milliseconds",
            self.precise_milliseconds_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "auto-list-view",
            self.automatic_list_view_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "recursive-parsing",
            self.recursive_parsing_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "follow-symlinks",
            self.follow_symlinks_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "load-compressed-covers",
            self.load_compressed_covers_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "compress-level",
            self.compress_level_adjustment,
            "value",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "autosave-throttling",
            self.autosave_throttling_adjustment,
            "value",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATELESS",
            "use-debug-log",
            self.enable_debug_logging_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        if Schema.auto_file_format == ".lrc":
            self.auto_file_manipulation_format.set_selected(0)
        elif Schema.auto_file_format == ".txt":
            self.auto_file_manipulation_format.set_selected(1)

    def _update_auto_file_format_schema(self, *_args) -> None:
        """Updates `shared.schema` with new preferred file format"""
        selected = self.auto_file_manipulation_format.get_selected()
        if selected == 0:
            Schema.STATELESS.set_string("auto-file-format", ".lrc")
        elif selected == 1:
            Schema.STATELESS.set_string("auto-file-format", ".txt")

    def _set_view_switcher_inactive(self, *_args) -> None:
        if self.automatic_list_view_switch.get_active():
            Constants.APP.lookup_action("view_type").set_enabled(False)
        else:
            Constants.APP.lookup_action("view_type").set_enabled(True)

    def _set_opened(self, opened: bool) -> None:
        """Controls possibility to open `self` only once at the time

        Parameters
        ----------
        opened : bool
            new `opened` value
        """
        self.__class__.opened = opened
