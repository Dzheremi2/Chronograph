from typing import Union

from gi.repository import Adw, Gtk

from chronograph.internal import Constants, Schema
from dgutils import GSingleton

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/Preferences.ui")
class ChronographPreferences(Adw.PreferencesDialog, metaclass=GSingleton):
  __gtype_name__ = "ChronographPreferences"

  reset_quick_edit_switch: Adw.SwitchRow = gtc()
  auto_file_manipulation_switch: Adw.SwitchRow = gtc()
  auto_file_manipulation_format: Adw.ComboRow = gtc()
  autosave_throttling_adjustment: Gtk.Adjustment = gtc()
  save_session_on_quit_switch: Adw.SwitchRow = gtc()
  precise_milliseconds_switch: Adw.SwitchRow = gtc()
  lbl_default_seek_adj: Gtk.Adjustment = gtc()
  lbl_large_seek_adj: Gtk.Adjustment = gtc()
  wbw_default_seek_adj: Gtk.Adjustment = gtc()
  wbw_large_seek_adj: Gtk.Adjustment = gtc()
  automatic_list_view_switch: Adw.SwitchRow = gtc()
  recursive_parsing_switch: Adw.ExpanderRow = gtc()
  follow_symlinks_switch: Adw.SwitchRow = gtc()
  load_compressed_covers_switch: Adw.ExpanderRow = gtc()
  compress_level_spin: Adw.SpinRow = gtc()
  compress_level_adjustment: Gtk.Adjustment = gtc()
  enable_debug_logging_switch: Adw.SwitchRow = gtc()
  syncing_type_combo_row: Adw.ComboRow = gtc()
  save_plain_lrc_also_switch_row: Adw.SwitchRow = gtc()
  elrc_prefix_entry_row: Adw.EntryRow = gtc()
  embed_lyrics_switch: Adw.ExpanderRow = gtc()
  use_individual_synced_tag_vorbis_switch: Adw.SwitchRow = gtc()
  embed_lyrics_default_toggle_group: Adw.ToggleGroup = gtc()

  _parse_recursively_unapplied = False
  _follow_symlinks_unapplied = False

  def __init__(self) -> None:
    super().__init__()

    self.auto_file_manipulation_format.connect(
      "notify::selected", self._update_auto_file_format_schema
    )
    self.automatic_list_view_switch.connect(
      "notify::active", self._set_view_switcher_inactive
    )
    self.syncing_type_combo_row.connect(
      "notify::selected", self._update_sync_type_schema
    )

    Schema.bind(
      "root.settings.file-manipulation.enabled",
      self.auto_file_manipulation_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.reset-quick-editor",
      self.reset_quick_edit_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.save-session",
      self.save_session_on_quit_switch,
      "active",
    )
    Schema.bind(
      "root.settings.syncing.precise",
      self.precise_milliseconds_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.auto-list-view",
      self.automatic_list_view_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.recursive-parsing.enabled",
      self.recursive_parsing_switch,
      "enable-expansion",
    )
    Schema.bind(
      "root.settings.general.recursive-parsing.follow-symlinks",
      self.follow_symlinks_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.compressed-covers.enabled",
      self.load_compressed_covers_switch,
      "enable-expansion",
    )
    Schema.bind(
      "root.settings.general.compressed-covers.level",
      self.compress_level_adjustment,
      "value",
    )
    Schema.bind(
      "root.settings.file-manipulation.throttling",
      self.autosave_throttling_adjustment,
      "value",
    )
    Schema.bind(
      "root.settings.general.debug-profile",
      self.enable_debug_logging_switch,
      "active",
    )
    Schema.bind(
      "root.settings.file-manipulation.lrc-along-elrc",
      self.save_plain_lrc_also_switch_row,
      "active",
    )
    Schema.bind(
      "root.settings.file-manipulation.embed-lyrics.vorbis",
      self.use_individual_synced_tag_vorbis_switch,
      "active",
    )
    Schema.bind(
      "root.settings.file-manipulation.embed-lyrics.default",
      self.embed_lyrics_default_toggle_group,
      "active-name",
    )
    Schema.bind(
      "root.settings.file-manipulation.elrc-prefix",
      self.elrc_prefix_entry_row,
      "text",
      preserve_cursor=True,
    )
    Schema.bind(
      "root.settings.file-manipulation.embed-lyrics.enabled",
      self.embed_lyrics_switch,
      "enable-expansion",
    )
    Schema.bind(
      "root.settings.syncing.seek.lbl.def",
      self.lbl_default_seek_adj,
      "value",
      transform_from=int,
      transform_to=float,
    )
    Schema.bind(
      "root.settings.syncing.seek.lbl.large",
      self.lbl_large_seek_adj,
      "value",
      transform_from=int,
      transform_to=float,
    )
    Schema.bind(
      "root.settings.syncing.seek.wbw.def",
      self.wbw_default_seek_adj,
      "value",
      transform_from=int,
      transform_to=float,
    )
    Schema.bind(
      "root.settings.syncing.seek.wbw.large",
      self.wbw_large_seek_adj,
      "value",
      transform_from=int,
      transform_to=float,
    )

    if Schema.get("root.settings.file-manipulation.format") == ".lrc":
      self.auto_file_manipulation_format.set_selected(0)
    elif Schema.get("root.settings.file-manipulation.format") == ".txt":
      self.auto_file_manipulation_format.set_selected(1)

    if Schema.get("root.settings.syncing.sync-type") == "lrc":
      self.syncing_type_combo_row.set_selected(0)
    elif Schema.get("root.settings.syncing.sync-type") == "wbw":
      self.syncing_type_combo_row.set_selected(1)

    self._parse_recursively = self.recursive_parsing_switch.get_enable_expansion()
    self._follow_symlinks = self.follow_symlinks_switch.get_active()
    self.recursive_parsing_switch.connect(
      "notify::enable-expansion", self._on_resursive_parsing_changed
    )
    self.follow_symlinks_switch.connect(
      "notify::active", self._on_resursive_parsing_changed
    )

  def _on_resursive_parsing_changed(
    self, row: Union[Adw.SwitchRow, Adw.ExpanderRow], _pspec
  ) -> None:
    if isinstance(row, Adw.SwitchRow):
      self._follow_symlinks_unapplied = row.get_active() != self._follow_symlinks
    elif isinstance(row, Adw.ExpanderRow):
      self._parse_recursively_unapplied = (
        row.get_enable_expansion() != self._parse_recursively
      )

    Constants.WIN.reparse_action_done = not any(
      (self._parse_recursively_unapplied, self._follow_symlinks_unapplied)
    )

  def on_reparse_banner_button_clicked(self) -> None:
    """Called on Window Re-parse banner button clicked to save new states of preferences as new default"""
    self._parse_recursively = self.recursive_parsing_switch.get_enable_expansion()
    self._follow_symlinks = self.follow_symlinks_switch.get_active()
    self._parse_recursively_unapplied = False
    self._follow_symlinks_unapplied = False

  def _update_auto_file_format_schema(self, *_args) -> None:
    selected = self.auto_file_manipulation_format.get_selected()
    if selected == 0:
      Schema.set("root.settings.file-manipulation.format", ".lrc")
    elif selected == 1:
      Schema.set("root.settings.file-manipulation.format", ".txt")

  def _update_sync_type_schema(self, *_args) -> None:
    selected = self.syncing_type_combo_row.get_selected()
    if selected == 0:
      Schema.set("root.settings.syncing.sync-type", "lrc")
    elif selected == 1:
      Schema.set("root.settings.syncing.sync-type", "wbw")

  def _set_view_switcher_inactive(self, *_args) -> None:
    if self.automatic_list_view_switch.get_active():
      Constants.APP.lookup_action("view_type").set_enabled(False)
    else:
      Constants.APP.lookup_action("view_type").set_enabled(True)
