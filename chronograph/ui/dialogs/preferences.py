from gi.repository import Adw, Gtk

from chronograph.internal import Constants, Schema
from dgutils import GSingleton

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/Preferences.ui")
class ChronographPreferences(Adw.PreferencesDialog, metaclass=GSingleton):
  __gtype_name__ = "ChronographPreferences"

  reset_quick_edit_switch: Adw.SwitchRow = gtc()
  autosave_throttling_adjustment: Gtk.Adjustment = gtc()
  save_library_on_quit_switch: Adw.SwitchRow = gtc()
  precise_milliseconds_switch: Adw.SwitchRow = gtc()
  lbl_default_seek_adj: Gtk.Adjustment = gtc()
  lbl_large_seek_adj: Gtk.Adjustment = gtc()
  wbw_default_seek_adj: Gtk.Adjustment = gtc()
  wbw_large_seek_adj: Gtk.Adjustment = gtc()
  parallel_downloadings_adj: Gtk.Adjustment = gtc()
  preferred_format_combo_row: Adw.ComboRow = gtc()
  enable_debug_logging_switch: Adw.SwitchRow = gtc()
  syncing_type_combo_row: Adw.ComboRow = gtc()
  do_lyrics_db_updates_switch: Adw.SwitchRow = gtc()
  save_plain_lrc_also_switch_row: Adw.SwitchRow = gtc()
  embed_lyrics_switch: Adw.ExpanderRow = gtc()
  use_individual_synced_tag_vorbis_switch: Adw.SwitchRow = gtc()
  embed_lyrics_default_toggle_group: Adw.ToggleGroup = gtc()

  def __init__(self) -> None:
    super().__init__()

    self.syncing_type_combo_row.connect(
      "notify::selected", self._update_sync_type_schema
    )
    self._setup_mass_downloading_preferred_format()

    Schema.bind(
      "root.settings.do-lyrics-db-updates.enabled",
      self.do_lyrics_db_updates_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.reset-quick-editor",
      self.reset_quick_edit_switch,
      "active",
    )
    Schema.bind(
      "root.settings.general.save-library",
      self.save_library_on_quit_switch,
      "active",
    )
    Schema.bind(
      "root.settings.syncing.precise",
      self.precise_milliseconds_switch,
      "active",
    )
    Schema.bind(
      "root.settings.do-lyrics-db-updates.throttling",
      self.autosave_throttling_adjustment,
      "value",
    )
    Schema.bind(
      "root.settings.general.debug-profile",
      self.enable_debug_logging_switch,
      "active",
    )
    Schema.bind(
      "root.settings.do-lyrics-db-updates.lrc-along-elrc",
      self.save_plain_lrc_also_switch_row,
      "active",
    )
    Schema.bind(
      "root.settings.do-lyrics-db-updates.embed-lyrics.vorbis",
      self.use_individual_synced_tag_vorbis_switch,
      "active",
    )
    Schema.bind(
      "root.settings.do-lyrics-db-updates.embed-lyrics.default",
      self.embed_lyrics_default_toggle_group,
      "active-name",
    )
    Schema.bind(
      "root.settings.do-lyrics-db-updates.embed-lyrics.enabled",
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
    Schema.bind(
      "root.settings.general.mass-downloading.parallel-amount",
      self.parallel_downloadings_adj,
      "value",
      transform_from=int,
      transform_to=float,
    )

    if Schema.get("root.settings.syncing.sync-type") == "lrc":
      self.syncing_type_combo_row.set_selected(0)
    elif Schema.get("root.settings.syncing.sync-type") == "wbw":
      self.syncing_type_combo_row.set_selected(1)

  def _setup_mass_downloading_preferred_format(self) -> None:
    def update_mass_downloading_preferred_format_schema(
      combo_row: Adw.ComboRow, _pspec
    ) -> None:
      selected = combo_row.get_selected()
      if selected < len(self.mass_downloading_preffered_format_keys):
        Schema.set(
          "root.settings.general.mass-downloading.preferred-format",
          self.mass_downloading_preffered_format_keys[selected],
        )

    preferred_format = Schema.get(
      "root.settings.general.mass-downloading.preferred-format"
    )
    string_list = Gtk.StringList()

    options = [
      ("s", _("Synced Only")),
      ("s~p", _("Synced, Fallback to Plain If Unavailable")),
      ("p", _("Plain Only")),
    ]
    self.mass_downloading_preffered_format_keys = [key for key, __ in options]
    for _key, display_name in options:
      string_list.append(display_name)

    self.preferred_format_combo_row.set_model(string_list)

    try:
      current_idx = self.mass_downloading_preffered_format_keys.index(preferred_format)
      self.preferred_format_combo_row.set_selected(current_idx)
    except ValueError:
      self.preferred_format_combo_row.set_selected(0)

    self.preferred_format_combo_row.connect(
      "notify::selected", update_mass_downloading_preferred_format_schema
    )

  def _update_sync_type_schema(self, *_args) -> None:
    selected = self.syncing_type_combo_row.get_selected()
    if selected == 0:
      Schema.set("root.settings.syncing.sync-type", "lrc")
    elif selected == 1:
      Schema.set("root.settings.syncing.sync-type", "wbw")
