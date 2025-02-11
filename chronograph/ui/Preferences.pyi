from gi.repository import Adw

class ChronographPreferences(Adw.PreferencesDialog):
    """Preferences dialog"""
    
    reset_quick_edit_switch: Adw.SwitchRow
    auto_file_manipulation_switch: Adw.ExpanderRow
    auto_file_manipulation_format: Adw.ComboRow
    save_session_on_quit_switch: Adw.SwitchRow
    precise_milliseconds_switch: Adw.SwitchRow

    opened: bool

    def update_auto_file_format_schema(self, *_args) -> None: ...
    def set_opened(self, opened: bool) -> None: ...