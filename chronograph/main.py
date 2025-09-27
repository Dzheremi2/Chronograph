import os
import sys
from pathlib import Path

import gi
import yaml

from chronograph.utils.player import Player

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GstPlay", "1.0")
gi.require_version("Gst", "1.0")

# pylint: disable=wrong-import-position,wrong-import-order
from gi.repository import Adw, Gdk, Gio, GLib, Gst, Gtk

# pylint: disable=ungrouped-imports
from chronograph.internal import Constants, Schema
from chronograph.logger import init_logger
from chronograph.window import ChronographWindow, WindowState
from dgutils.decorators import singleton

logger = Constants.LOGGER
Gst.init(None)


@singleton
class ChronographApplication(Adw.Application):
    """Application class"""

    win: ChronographWindow

    def __init__(self) -> None:
        super().__init__(
            application_id=Constants.APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_resource_path(Constants.PREFIX + "/data/icons")
        self.paths = []
        self.connect("open", self.on_open)

    def on_open(self, _app, files: list, *_args) -> None:
        """Implicates an ability to open files within the app from file manager

        Parameters
        ----------
        app : self
            app itself
        files : list
            files passed from the file manager
        """
        for file in files:
            path = file.get_path()
            if path:
                if os.path.isdir(path):
                    pass
                else:
                    self.paths.append(path)
        logger.info("Requesting opening for files:\n%s", "\n".join(self.paths))
        self.do_activate()

    def do_activate(self) -> None:  # pylint: disable=arguments-differ
        """Emits on app creation"""

        win = self.props.active_window  # pylint: disable=no-member
        if not win:
            Constants.WIN = win = ChronographWindow(application=self)
        else:
            Constants.WIN = win
        logger.debug("Window was created")

        self.create_actions(
            {
                # fmt: off
                ("quit",("<primary>q","<primary>w",),),
                ("toggle_sidebar", ("F9",), Constants.WIN),
                ("toggle_search", ("<primary>f",), Constants.WIN),
                ("select_dir", ("<primary><shift>o",), Constants.WIN),
                ("select_files", ("<primary>o",), Constants.WIN),
                ("show_preferences", ("<primary>comma",), Constants.WIN),
                ("open_quick_editor", (), Constants.WIN),
                ("about",),
                # fmt: on
            }
        )
        self.set_accels_for_action("win.show-help-overlay", ("<primary>question",))

        sorting_action = Gio.SimpleAction.new_stateful(
            "sort_type",
            GLib.VariantType.new("s"),
            GLib.Variant("s", Schema.get("root.state.library.sorting")),
        )
        sorting_action.connect("activate", Constants.WIN.on_sort_type_action)
        self.add_action(sorting_action)

        view_action = Gio.SimpleAction.new_stateful(
            "view_type",
            GLib.VariantType.new("s"),
            GLib.Variant("s", Schema.get("root.state.library.view")),
        )
        view_action.connect("activate", Constants.WIN.on_view_type_action)
        self.add_action(view_action)

        Schema.bind("root.state.window.width", Constants.WIN, "default-width")
        Schema.bind(
            "root.state.window.height",
            Constants.WIN,
            "default-height",
        )
        Schema.bind(
            "root.state.window.maximized",
            Constants.WIN,
            "maximized",
        )

        if Schema.get("root.settings.general.auto-list-view"):
            self.lookup_action("view_type").set_enabled(False)
        else:
            self.lookup_action("view_type").set_enabled(True)

        if (
            (path := Schema.get("root.state.library.session")) != "None"
            and os.path.exists(Schema.get("root.state.library.session"))
            and len(self.paths) == 0
        ):
            logger.info("Loading last opened session: '%s'", path)
            Constants.WIN.open_directory(path)
        elif len(self.paths) != 0:
            logger.info("Opening requested files")
            Constants.WIN.open_files(self.paths)
        else:
            Constants.WIN.set_property("state", WindowState.EMPTY)

        Constants.WIN.present()
        logger.debug("Window shown")

        Player().set_property("playback_rate", 2.0)

    def on_about_action(self, *_args) -> None:
        """Shows About App dialog"""

        def _get_debug_info() -> str:
            if os.path.exists(
                os.path.join(
                    Constants.CACHE_DIR, "chronograph", "logs", "chronograph.log"
                )
            ):
                with open(
                    os.path.join(
                        Constants.CACHE_DIR, "chronograph", "logs", "chronograph.log"
                    )
                ) as f:
                    return f.read()
            return "No log availble yet"

        dialog = Adw.AboutDialog.new_from_appdata(
            Constants.PREFIX + "/" + Constants.APP_ID + ".metainfo.xml",
            Constants.VERSION,
        )
        dialog.set_developers(
            ("Dzheremi https://github.com/Dzheremi2", "ahi https://github.com/ahi6")
        )
        dialog.set_designers(("Dzheremi https://github.com/Dzheremi2",))
        # Translators: Add Your Name, Your Name <your.email@example.com>, or Your Name https://your-site.com for it to show up in the About dialog. PLEASE, DON'T DELETE PREVIOUS TRANSLATORS CREDITS AND SEPARATE YOURSELF BY NEWLINE `\n` METASYMBOL
        dialog.set_translator_credits(_("translator-credits"))
        dialog.set_copyright("© 2024-2025 Dzheremi")
        dialog.add_legal_section(
            "LRClib",
            "© 2024 tranxuanthang",
            Gtk.License.MIT_X11,
        )
        dialog.add_acknowledgement_section(
            _("Inspiration"),
            (
                "knuxify (Ear Tag) https://gitlab.gnome.org/World/eartag",
                "kra-mo (Cartridges) https://github.com/kra-mo/cartridges",
            ),
        )
        dialog.add_other_app(
            "io.github.dzheremi2.lexi",
            "Lexi",
            # Translators: This is the summary of the another app Lexi: https://flathub.org/apps/io.github.dzheremi2.lexi
            _("Build your own dictionary"),
        )

        dialog.set_debug_info(_get_debug_info())
        dialog.set_debug_info_filename("chronograph.log")
        dialog.add_link(
            _("Translate the App"), "https://hosted.weblate.org/engage/chronograph/"
        )

        if Constants.PREFIX.endswith("Devel"):
            dialog.set_version("Devel")
        logger.debug("Showing about dialog")
        dialog.present(Constants.WIN)

    def on_quit_action(self, *_args) -> None:
        self.quit()

    def do_shutdown(self):  # pylint: disable=arguments-differ
        Player().stop()
        if not Schema.get("root.settings.general.save-session"):
            logger.info("Resetting session")
            Schema.set("root.state.library.session", "None")
        Schema._save()  # pylint: disable=protected-access

        Constants.CACHE_FILE.seek(0)
        Constants.CACHE_FILE.truncate(0)
        yaml.dump(
            Constants.CACHE,
            Constants.CACHE_FILE,
            sort_keys=False,
            encoding=None,
            allow_unicode=True,
        )
        logger.info("Cache saved")
        logger.info("App was closed")

    def create_actions(self, actions: set) -> None:
        """Creates actions for provided scope with provided accels

        Args:
            actions (set): Actions in format ("name", ("accels",), scope)

            accels, scope: optional
        """
        for action in actions:
            simple_action = Gio.SimpleAction.new(action[0], None)

            scope = action[2] if action[2:3] else self
            simple_action.connect("activate", getattr(scope, f"on_{action[0]}_action"))

            if action[1:2]:
                self.set_accels_for_action(
                    f"app.{action[0]}" if scope == self else f"win.{action[0]}",
                    action[1],
                )
            scope.add_action(simple_action)
            logger.debug(
                "Created action for %s with accels %s",
                action[0],
                action[1] if action[1:2] else None,
            )


def main(_version):
    """App entrypoint"""
    init_logger()
    logger.info("Launching application")
    if not "cache.yaml" in os.listdir(Constants.DATA_DIR):
        logger.info("The cache file does not exist, creating")
        file = open(str(Constants.DATA_DIR) + "/cache.yaml", "x+")
        file.write("pins: []\ncache_version: 2")
        file.close()

    Constants.CACHE_FILE = open(
        str(Constants.DATA_DIR) + "/cache.yaml", "r+", encoding="utf-8"
    )
    Constants.CACHE = yaml.safe_load(Constants.CACHE_FILE)
    logger.info("Cache loaded successfully")

    if "session" in Constants.CACHE:
        Constants.CACHE.pop("session", None)
        Constants.CACHE["cache_version"] = 2
    Constants.APP = app = ChronographApplication()
    return app.run(sys.argv)
