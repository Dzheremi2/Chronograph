from pathlib import Path

from gi.repository import GObject, Gst, GstPlay, Gtk

from chronograph.internal import Constants, Schema
from dgutils.decorators import singleton

logger = Constants.PLAYER_LOGGER


@singleton
class GstPlayer(GstPlay.Play):
    __gtype_name__ = "GstPlayer"

    __gsignals__ = {
        "eos": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "no-resource": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "err": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "pos-upd": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "duration-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "seek-done": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()

        self.set_volume(0)
        self.name = "Player"

        self.prerolled = False
        self.pipeline: Gst.Pipeline = self.get_pipeline()

        bus: Gst.Bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        play_bus: Gst.Bus = self.get_message_bus()
        play_bus.add_signal_watch()
        play_bus.connect("message", self._on_play_bus_message)

    def _on_play_bus_message(self, _bus, msg: GstPlay.PlayMessage) -> None:
        match GstPlay.PlayMessage.parse_type(msg):
            case GstPlay.PlayMessage.POSITION_UPDATED:
                self.emit("pos-upd", GstPlay.PlayMessage.parse_position_updated(msg))
            case GstPlay.PlayMessage.DURATION_CHANGED:
                self.emit(
                    "duration-changed",
                    GstPlay.PlayMessage.parse_duration_changed(msg),
                )
            case GstPlay.PlayMessage.SEEK_DONE:
                self.emit("seek-done")

    def _on_bus_message(self, _bus, message: Gst.Message) -> None:
        if message:
            if message.type == Gst.MessageType.BUFFERING:
                if message.percentage < 100:
                    self.pause()
                    logger.info("Buffering")
                else:
                    self.play()
                    logger.info("Buffering completed")
            elif message.type == Gst.MessageType.EOS:
                self.emit("eos")
            elif message.type == Gst.MessageType.ERROR:
                error, debug_msg = message.parse_error()

                if error.code == Gst.ResourceError.NOT_FOUND:
                    self.stop()
                    self.emit("no-resource")
                    logger.warning("Resource not found. Player stopped")
                    return

                logger.error("%s: %s", error.code, error)
                logger.debug(debug_msg)

    def _is_player_loaded(self) -> bool:
        __, state, ___ = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        return state in (Gst.State.PLAYING, Gst.State.PAUSED)

    @property
    def state(self) -> Gst.State:
        if not self._is_player_loaded():
            return Gst.State.READY

        __, state, ___ = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        if state == Gst.State.PLAYING:
            return Gst.State.PLAYING
        if state == Gst.State.PAUSED:
            return Gst.State.PAUSED
        logger.debug("Player state is not PLAYING or PAUSED. STATE: %s", state.name)
        return Gst.State.READY


@singleton
class Player(GObject.Object):
    __gtype_name__ = "Player"

    _cookie = 0

    playing: bool = GObject.Property(type=bool, default=False)
    volume: float = GObject.Property(type=float, default=1.0)
    rate: float = GObject.Property(type=float, default=1.0)
    mute: bool = GObject.Property(type=bool, default=False)
    pos: int = GObject.Property(type=GObject.TYPE_INT64, default=0)
    duration: int = GObject.Property(type=GObject.TYPE_INT64, default=-1)

    looped: bool = False

    def __init__(self):
        super().__init__()
        self._gst_player = GstPlayer()
        self.bind_property(
            "volume", self._gst_player, "volume", GObject.BindingFlags.SYNC_CREATE
        )
        self.bind_property(
            "mute", self._gst_player, "mute", GObject.BindingFlags.SYNC_CREATE
        )
        self.bind_property(
            "rate", self._gst_player, "rate", GObject.BindingFlags.SYNC_CREATE
        )
        Schema.bind("root.state.player.mute", self, "mute")
        Schema.bind(
            "root.state.player.volume",
            self,
            "volume",
            transform_to=lambda val: round(float(val / 100), 2),
            transform_from=lambda val: int(val * 100)
        )
        Schema.bind("root.state.player.rate", self, "rate")
        self._gst_player.connect("eos", self._on_eos)
        self._gst_player.connect(
            "pos-upd", lambda _, pos: self.set_property("pos", pos)
        )
        self._gst_player.connect(
            "duration-changed",
            lambda _, duration: self.set_property("duration", duration),
        )
        self.connect("notify::playing", self._on_playing)

    def set_file(self, file: Path) -> None:
        self._gst_player.props.uri = file.as_uri()
        logger.info("File “%s” set to player", str(file))
        self._gst_player.pause()

    def inhibit(self, inhibit: bool) -> None:
        app = Gtk.Application.get_default()
        if inhibit:
            if self._cookie:
                return

            self._cookie = app.inhibit(
                None, Gtk.ApplicationInhibitFlags.SUSPEND, "Playback in progress"
            )
            logger.debug(
                "Application inhibited to prevent playing media app from being suspended"
            )
        elif self._cookie != 0:
            app.uninhibit(self._cookie)
            logger.debug("Application uninhibited")
            self._cookie = 0

    def seek(self, new_pos: int) -> None:
        """Seeks the player to a new position

        Parameters
        ----------
        new_pos : int
            Position in milliseconds
        """
        pos = new_pos * Gst.MSECOND
        self._gst_player.pipeline.seek(
            self.rate,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH,
            Gst.SeekType.SET,
            pos,
            Gst.SeekType.NONE,
            0,
        )
        logger.debug("Seeked to %sns", pos)

    def stop(self) -> None:
        self._gst_player.stop()
        self.props.playing = False
        self.inhibit(False)
        logger.info("Player stopped")

    def _on_eos(self, *_args) -> None:
        vol = self.volume
        rate = self.rate
        self.seek(0)
        if not self.looped:
            self.set_property("playing", False)
            self._gst_player.pause()
            logger.info("Stream ended")
        else:
            self._gst_player.play()
            self.set_property("volume", vol)
            self.set_property("rate", rate)

    def _on_playing(self, *_args) -> None:
        self.inhibit(self.playing)

    def play_pause(self) -> None:
        if self._gst_player.state in (Gst.State.PAUSED, Gst.State.READY):
            self._gst_player.play()
        elif self._gst_player.state == Gst.State.PLAYING:
            self._gst_player.pause()
        else:
            logger.warning("Trying to play/pause player in STOP state")
