import os
import sys

import gi
import yaml

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from chronograph.internal import Constants, Schema
from chronograph.window import ChronographWindow


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
        # self.connect("open", self.on_open)

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
        self.do_activate()

    def do_activate(self) -> None:  # pylint: disable=arguments-differ
        """Emits on app creation"""

        win = self.props.active_window  # pylint: disable=no-member
        if not win:
            Constants.WIN = win = ChronographWindow(application=self)
        else:
            Constants.WIN = win

        self.create_actions(
            {
                # fmt: off
                ("quit",("<primary>q","<primary>w",),),
                ("toggle_sidebar", ("F9",), Constants.WIN),
                ("toggle_search", ("<primary>f",), Constants.WIN),
                ("select_dir", ("<primary><shift>o",), Constants.WIN),
                ("select_files", ("<primary>o",), Constants.WIN),
                # ("search_lrclib", (), shared.win),
                # ("import_lyrics_lrclib_synced", (), shared.win),
                # ("import_lyrics_lrclib_plain", (), shared.win),
                # ("show_preferences", ("<primary>comma",), shared.win),
                # ("open_quick_editor", (), shared.win),
                ("about",),
                # fmt: on
            }
        )
        self.set_accels_for_action("win.show-help-overlay", ("<primary>question",))

        sorting_action = Gio.SimpleAction.new_stateful(
            "sort_type",
            GLib.VariantType.new("s"),
            GLib.Variant("s", Schema.sorting),
        )
        sorting_action.connect("activate", Constants.WIN.on_sort_type_action)
        self.add_action(sorting_action)

        # view_action = Gio.SimpleAction.new_stateful(
        #     "view_type",
        #     GLib.VariantType.new("s"),
        #     view_mode := GLib.Variant("s", shared.state_schema.get_string("view")),
        # )
        # view_action.connect("activate", shared.win.on_view_type_action)
        # self.add_action(view_action)

        Schema.bind(
            "STATEFULL",
            "window-width",
            Constants.WIN,
            "default-width",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATEFULL",
            "window-height",
            Constants.WIN,
            "default-height",
            Gio.SettingsBindFlags.DEFAULT,
        )
        Schema.bind(
            "STATEFULL",
            "window-maximized",
            Constants.WIN,
            "maximized",
            Gio.SettingsBindFlags.DEFAULT,
        )

        # if (path := shared.cache["session"]) is not None and len(self.paths) == 0:
        #     dir_parser(path)
        #     del path
        # elif len(self.paths) != 0:
        #     if parse_files(self.paths):
        #         shared.win.state = WindowState.LOADED_FILES
        #     else:
        #         shared.win.state = WindowState.EMPTY
        # else:
        #     shared.win.state = WindowState.EMPTY

        # if shared.schema.get_boolean("auto-list-view"):
        #     shared.app.lookup_action("view_type").set_enabled(False)
        # else:
        #     shared.app.lookup_action("view_type").set_enabled(True)

        Constants.WIN.present()

    def on_about_action(self, *_args) -> None:
        """Shows About App dialog"""
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

        if Constants.PREFIX.endswith("Devel"):
            dialog.set_version("Devel")
        dialog.present(Constants.WIN)

    def on_quit_action(self, *_args) -> None:
        self.quit()

    def do_shutdown(self):  # pylint: disable=arguments-differ
        if Schema.save_session and (Schema.opened_dir != "None"):
            Constants.CACHE["session"] = Schema.STATEFULL.get_string("opened-dir")[:-1]
        else:
            Constants.CACHE["session"] = None

        Constants.CACHE_FILE.seek(0)
        Constants.CACHE_FILE.truncate(0)
        yaml.dump(
            Constants.CACHE,
            Constants.CACHE_FILE,
            sort_keys=False,
            encoding=None,
            allow_unicode=True,
        )

        Schema.opened_dir = "None"

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


def main(_version):
    """App entrypoint"""
    if not "cache.yaml" in os.listdir(Constants.DATA_DIR):
        file = open(str(Constants.DATA_DIR) + "/cache.yaml", "x+")
        file.write("pins: []\nsession: null\ncache_version: 1")
        file.close()

    Constants.CACHE_FILE = open(
        str(Constants.DATA_DIR) + "/cache.yaml", "r+", encoding="utf-8"
    )
    Constants.CACHE = yaml.safe_load(Constants.CACHE_FILE)
    Constants.APP = app = ChronographApplication()
    return app.run(sys.argv)
