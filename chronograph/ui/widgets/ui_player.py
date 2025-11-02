from pathlib import Path

from gi.repository import Adw, GObject, Gst, Gtk

from chronograph.backend.file.song_card_model import SongCardModel
from chronograph.backend.player import Player
from chronograph.internal import Constants, Schema

gtc = Gtk.Template.Child
player_logger = Constants.PLAYER_LOGGER


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/UIPlayer.ui")
class UIPlayer(Adw.BreakpointBin):
  __gtype_name__ = "UIPlayer"

  main_clamp: Adw.Clamp = gtc()
  sync_page_cover: Gtk.Image = gtc()
  title_inscr: Gtk.Inscription = gtc()
  artist_inscr: Gtk.Inscription = gtc()
  non_collapse_box: Gtk.Box = gtc()
  player_box: Gtk.Box = gtc()
  toggle_play_button: Gtk.Button = gtc()
  elapsed_time_label: Gtk.Label = gtc()
  seekbar: Gtk.Scale = gtc()
  position_adj: Gtk.Adjustment = gtc()
  remaining_time_label: Gtk.Label = gtc()
  volume_button: Gtk.Button = gtc()
  volume_adj: Gtk.Adjustment = gtc()
  volume_label: Gtk.Label = gtc()
  rate_adj: Gtk.Adjustment = gtc()
  rate_label: Gtk.Label = gtc()
  repeat_button: Gtk.ToggleButton = gtc()
  collapse_box: Gtk.Box = gtc()

  def __init__(
    self,
    card_model: SongCardModel,
    max_width: int = 600,
  ) -> None:
    super().__init__()
    Player().set_file(Path(card_model.path))

    # Init Playback GUI setup
    vol = int(Player().volume * 100)
    self._on_volume(None, None, vol)
    self.volume_label.set_label(_("{vol}%").format(vol=vol))
    self.volume_adj.set_value(vol)
    self.rate_adj.set_value(Player().rate)
    self.rate_label.set_label(f"{Player().rate}x")
    if Schema.get("root.state.player.mute"):
      self.volume_button.set_icon_name("chr-vol-mute-symbolic")

    # Playback UI Reactivity
    self.pos_hndl = Player().connect("notify::pos", self._on_pos_changed)
    self.playing_hndl = Player().connect("notify::playing", self._on_playing_changed)
    self.volume_hndl = Player().connect(
      "notify::volume",
      lambda *__: self.volume_label.set_label(
        _("{vol}%").format(vol=int(Player().volume * 100))
      ),
    )
    self.duration_hndl = Player().connect(
      "notify::duration",
      lambda *__: [
        self.position_adj.set_upper(Player().duration / Gst.SECOND),
        self._on_pos_changed(Player(), None),
      ],
    )
    self.rate_hndl = Player().connect(
      "notify::rate",
      lambda *__: self.rate_label.set_label(f"{Player().rate}x"),
    )
    self.seek_done_hndl = Player()._gst_player.connect("seek-done", self._on_seek_done)  # noqa: SLF001

    # Info UI reactivity
    self._card = card_model
    self.main_clamp.set_maximum_size(max_width)
    self.main_clamp.set_tightening_threshold(max_width)

    self.title_display_bind = self._card.bind_property(
      "title_display",
      self.title_inscr,
      "text",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.artist_display_bind = self._card.bind_property(
      "artist_display",
      self.artist_inscr,
      "text",
      GObject.BindingFlags.SYNC_CREATE,
    )
    self.cover_bind = self._card.bind_property(
      "cover",
      self.sync_page_cover,
      "paintable",
      GObject.BindingFlags.SYNC_CREATE,
    )

  def disconnect_all(self) -> None:
    """Removes all reactivity from `self`.

    Used on page closure to not update all other `UIPlayer` instances for each media
    (since Gtk.Widgets are not destroyed and cannot be)
    """
    self.disconnect(self.pos_hndl)
    self.disconnect(self.volume_hndl)
    self.disconnect(self.playing_hndl)
    self.disconnect(self.duration_hndl)
    self.disconnect(self.rate_hndl)
    self.disconnect(self.seek_done_hndl)
    self.title_display_bind.unbind()
    self.artist_display_bind.unbind()
    self.cover_bind.unbind()

  @Gtk.Template.Callback()
  def _toggle_play(self, *_args) -> None:
    if Player().playing:
      Player().set_property("playing", False)
    else:
      Player().set_property("playing", True)
    Player().play_pause()
    self._on_playing_changed(Player(), None)

  def _on_playing_changed(self, player: Player, _pspec) -> None:
    playing = player.playing
    if playing:
      self.toggle_play_button.set_icon_name("chr-pause-symbolic")
    else:
      self.toggle_play_button.set_icon_name("play-button-symbolic")

  def _on_pos_changed(self, player: Player, _pspec) -> None:
    pos = player.pos
    seconds = pos // Gst.SECOND
    self.position_adj.props.value = seconds
    mm, ss = divmod(seconds, 60)
    elapsed_string = f"{mm:02d}:{ss:02d}"

    if not player.duration < 0:
      remain = player.duration - pos
      remain_seconds = remain // Gst.SECOND
      mm, ss = divmod(remain_seconds, 60)
      remain_string = f"-{mm:02d}:{ss:02d}"
    else:
      remain_string = "--:--"

    self.elapsed_time_label.props.label = elapsed_string
    self.remaining_time_label.props.label = remain_string

  def _on_seek_done(self, *_args) -> None:
    pos = Player()._gst_player.props.position  # noqa: SLF001
    self.seekbar.set_value(pos / Gst.SECOND)

  @Gtk.Template.Callback()
  def _on_volume(self, _, __, val: float) -> None:
    self.volume_button.remove_css_class("destructive-action")
    if 0.0 < val <= 33.0:
      self.volume_button.set_icon_name("chr-vol-min-symbolic")
    elif 33.0 < val <= 66.0:
      self.volume_button.set_icon_name("chr-vol-middle-symbolic")
    elif 66.0 < val < 101.0:
      self.volume_button.set_icon_name("chr-vol-max-symbolic")
    elif val >= 101.0:
      self.volume_button.set_icon_name("chr-vol-max-symbolic")
      self.volume_button.add_css_class("destructive-action")
    elif val < 0:
      val = 0
    else:
      self.volume_button.set_icon_name("chr-vol-mute-symbolic")
    if Player().mute:
      Player().set_property("mute", False)
    Player().set_property("volume", round(val) / 100)

  @Gtk.Template.Callback()
  def _on_rate(self, _, __, val: float) -> None:
    Player().set_property("rate", max(0.1, round(val, 1)))

  @Gtk.Template.Callback()
  def _toggle_mute(self, *_args) -> None:
    Player().set_property("mute", not Player().mute)
    if Player().mute:
      self.volume_button.set_icon_name("chr-vol-mute-symbolic")
      self.volume_button.remove_css_class("destructive-action")
      self.volume_adj.set_value(0)
    else:
      vol = Schema.get("root.state.player.volume")
      self.volume_adj.set_value(vol)
      self._on_volume(None, None, vol)

  @Gtk.Template.Callback()
  def _on_reset(self, *_args) -> None:
    self.rate_adj.set_value(1.0)
    Player().set_property("rate", 1.0)
    Schema.set("root.state.player.rate", 1.0)
    self.volume_adj.set_value(100.0)
    Player().set_property("volume", 1.0)
    Schema.set("root.state.player.volume", 100)

  @Gtk.Template.Callback()
  def _on_seekbar_value(self, _rng, _scrl, value: float) -> None:
    Player().seek(value * 1_000)

  @Gtk.Template.Callback()
  def _on_breakpoint(self, *_args) -> None:
    if self.collapse_box.get_first_child() is None:
      self.non_collapse_box.remove(self.player_box)
      self.collapse_box.append(self.player_box)
    else:
      self.collapse_box.remove(self.player_box)
      self.non_collapse_box.append(self.player_box)

  @Gtk.Template.Callback()
  def _on_repeat_button_toggled(self, button: Gtk.ToggleButton) -> None:
    Player().looped = button.get_active()
    player_logger.debug("Playback loop was set to: %s", button.get_active())
