import os
import sys

import gi
import yaml

from chronograph.utils.parsers import dir_parser, parse_files

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # type: ignore

from chronograph import shared
from chronograph.window import ChronographWindow, WindowState


class ChronographApplication(Adw.Application):
    """Application class"""

    win: ChronographWindow

    def __init__(self) -> None:
        super().__init__(
            application_id=shared.APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_resource_path(shared.PREFIX + "/data/icons")
        self.paths = []
        self.connect("open", self.on_open)

    def on_open(self, app, files: list, *_args) -> None:
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
            shared.win = win = ChronographWindow(application=self)
        else:
            shared.win = win

        self.create_actions(
            {
                # fmt: off
                ("quit",("<primary>q","<primary>w",),),
                ("toggle_sidebar", ("F9",), shared.win),
                ("toggle_search", ("<primary>f",), shared.win),
                ("select_dir", ("<primary><shift>o",), shared.win),
                ("select_files", ("<primary>o",), shared.win),
                ("append_line", ("<Alt><primary>a",), shared.win),
                ("remove_selected_line", ("<Alt>r",), shared.win),
                ("append_selected_line", ("<Alt>a",), shared.win),
                ("prepend_selected_line", ("<Alt>p",), shared.win),
                ("sync_line", ("<Alt>Return",), shared.win),
                ("replay_line", ("<Alt>z",), shared.win),
                ("100ms_rew", ("<Alt>minus",), shared.win),
                ("100ms_forw", ("<Alt>equal",), shared.win),
                ("show_file_info", (), shared.win),
                ("import_from_clipboard", (), shared.win),
                ("import_from_file", (), shared.win),
                ("import_from_lrclib", (), shared.win),
                ("search_lrclib", (), shared.win),
                ("import_lyrics_lrclib_synced", (), shared.win),
                ("import_lyrics_lrclib_plain", (), shared.win),
                ("export_to_file", (), shared.win),
                ("export_to_clipboard", (), shared.win),
                ("export_to_lrclib", (), shared.win),
                ("show_preferences", ("<primary>comma",), shared.win),
                ("open_quick_editor", (), shared.win),
                ("about",),
                # fmt: on
            }
        )
        self.set_accels_for_action("win.show-help-overlay", ("<primary>question",))

        sorting_action = Gio.SimpleAction.new_stateful(
            "sort_type",
            GLib.VariantType.new("s"),
            sorting_mode := GLib.Variant(
                "s", shared.state_schema.get_string("sorting")
            ),
        )
        sorting_action.connect("activate", shared.win.on_sorting_type_action)
        self.add_action(sorting_action)

        view_action = Gio.SimpleAction.new_stateful(
            "view_type",
            GLib.VariantType.new("s"),
            view_mode := GLib.Variant("s", shared.state_schema.get_string("view")),
        )
        view_action.connect("activate", shared.win.on_view_type_action)
        self.add_action(view_action)

        shared.state_schema.bind(
            "window-width", shared.win, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        shared.state_schema.bind(
            "window-height", shared.win, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        shared.state_schema.bind(
            "window-maximized", shared.win, "maximized", Gio.SettingsBindFlags.DEFAULT
        )

        if (path := shared.cache["session"]) is not None and len(self.paths) == 0:
            dir_parser(path)
            del path
        elif len(self.paths) != 0:
            if parse_files(self.paths):
                shared.win.state = WindowState.LOADED_FILES
            else:
                shared.win.state = WindowState.EMPTY
        else:
            shared.win.state = WindowState.EMPTY

        if shared.schema.get_boolean("auto-list-view"):
            shared.app.lookup_action("view_type").set_enabled(False)
        else:
            shared.app.lookup_action("view_type").set_enabled(True)

        shared.win.present()

    def on_about_action(self, *_args) -> None:
        """Shows About App dialog"""
        dialog = Adw.AboutDialog.new_from_appdata(
            shared.PREFIX + "/" + shared.APP_ID + ".metainfo.xml", shared.VERSION
        )
        dialog.set_developers(("Dzheremi https://github.com/Dzheremi2",))
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
            None, ("knuxify (Ear Tag) https://gitlab.gnome.org/World/eartag",)
        )
        dialog.add_other_app(
            "io.github.dzheremi2.lexi",
            "Lexi",
            _("Build your own dictionary")
        )

        if shared.PREFIX.endswith("Devel"):
            dialog.set_version("Devel")
        dialog.present(shared.win)

    def on_quit_action(self, *_args) -> None:
        self.quit()

    def do_shutdown(self):
        if shared.schema.get_boolean("save-session") and (
            shared.state_schema.get_string("opened-dir") != "None"
        ):
            shared.cache["session"] = shared.state_schema.get_string("opened-dir")[:-1]
        else:
            shared.cache["session"] = None

        shared.cache_file.seek(0)
        shared.cache_file.truncate(0)
        yaml.dump(
            shared.cache,
            shared.cache_file,
            sort_keys=False,
            encoding=None,
            allow_unicode=True,
        )

        shared.state_schema.set_string("opened-dir", "None")

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
    if not ("cache.yaml" in os.listdir(shared.data_dir)):
        file = open(str(shared.data_dir) + "/cache.yaml", "x+")
        file.write("pins: []\nsession: null\ncache_version: 1")
        file.close()

    shared.cache_file = open(
        str(shared.data_dir) + "/cache.yaml", "r+", encoding="utf-8"
    )
    shared.cache = yaml.safe_load(shared.cache_file)
    shared.app = app = ChronographApplication()
    return app.run(sys.argv)
