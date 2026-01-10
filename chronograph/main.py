import os
import sys
from pathlib import Path

import gi
import yaml

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GstPlay", "1.0")
gi.require_version("Gst", "1.0")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gst, Gtk

from chronograph.backend.player import Player
from chronograph.internal import Constants, Schema
from chronograph.logger import init_logger
from chronograph.window import ChronographWindow, WindowState

logger = Constants.LOGGER
Gst.init(None)


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
        if Path(path).is_dir():
          pass
        else:
          self.paths.append(path)
    logger.info("Requesting opening for files:\n%s", "\n".join(self.paths))
    self.do_activate()

  def do_activate(self) -> None:
    """Emits on app creation"""
    win = self.props.active_window
    if not win:
      Constants.WIN = win = ChronographWindow(application=self)
    else:
      Constants.WIN = win
    logger.debug("Window was created")

    last_library = Schema.get("root.state.library.last-library")
    last_library_path = Path(last_library) if last_library else None
    if (
      last_library_path
      and last_library != "None"
      and (last_library_path / "is_chr_library").exists()
      and Constants.WIN.open_library(last_library)
    ):
      if self.paths:
        Constants.WIN.import_files_to_library(self.paths)
        self.paths = []
    elif self.paths:
      Constants.WIN.show_toast(_("Open a library before importing files"), 3)
      self.paths = []
    else:
      Constants.WIN.set_property("state", WindowState.NO_LIBRARY)

    # fmt: off
    self.create_actions(
      {
        ("quit", ("<primary>q", "<primary>w")),
        ("toggle_sidebar", ("F9",), Constants.WIN),
        ("toggle_search", ("<primary>f",), Constants.WIN),
        ("open_library", ("<primary><shift>o",), Constants.WIN),
        ("import_files", ("<primary>o",), Constants.WIN),
        ("create_library", (), Constants.WIN),
        ("register_tag", (), Constants.WIN),
        ("show_preferences", ("<primary>comma",), Constants.WIN),
        ("open_quick_editor", (), Constants.WIN),
        ("open_mass_downloading", (), Constants.WIN),
        ("about",),
      }
    )
    # fmt: on
    self.set_accels_for_action("win.show-help-overlay", ("<primary>question",))

    sort_type_action = Gio.SimpleAction.new_stateful(
      "sort_type",
      GLib.VariantType.new("s"),
      GLib.Variant("s", Schema.get("root.state.library.sorting.sort-type")),
    )
    sort_type_action.connect("activate", Constants.WIN.on_sort_type_action)
    self.add_action(sort_type_action)

    sort_mode_action = Gio.SimpleAction.new_stateful(
      "sort_mode",
      GLib.VariantType.new("s"),
      GLib.Variant("s", Schema.get("root.state.library.sorting.sort-mode")),
    )
    sort_mode_action.connect("activate", Constants.WIN.on_sort_type_action)
    self.add_action(sort_mode_action)

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

    Constants.WIN.present()
    Player().set_property("volume", float(Schema.get("root.state.player.volume") / 100))
    Player().set_property("rate", float(Schema.get("root.state.player.rate")))
    logger.debug("Window shown")

  def on_about_action(self, *_args) -> None:
    """Shows About App dialog"""

    def _get_debug_info() -> str:
      if Path(
        os.path.join(Constants.CACHE_DIR, "chronograph", "logs", "chronograph.log")
      ).exists():
        with open(
          os.path.join(Constants.CACHE_DIR, "chronograph", "logs", "chronograph.log"),
          encoding="utf-8",
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

    # Should fix app icon missing in dialog on windows
    if sys.platform == "win32":
      dialog.set_application_icon("chr-app-icon")

    dialog.set_designers(
      (
        "Dzheremi https://github.com/Dzheremi2",
        "Ignacy Kuchciński https://gitlab.gnome.org/ignapk",
        "Martin Abente Lahaye https://gitlab.gnome.org/tchx84",
      )
    )
    # Translators: Add Your Name, Your Name <your.email@example.com>, or Your Name https://your-site.com for it to show up in the About dialog. PLEASE, DON'T DELETE PREVIOUS TRANSLATORS CREDITS AND SEPARATE YOURSELF BY NEWLINE `\n` METASYMBOL
    dialog.set_translator_credits(_("translator-credits"))
    dialog.set_copyright("© 2024-2026 Dzheremi")
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
    elif "-rc" in Constants.VERSION:
      dialog.set_version(Constants.VERSION)

    logger.debug("Showing about dialog")
    dialog.present(Constants.WIN)

  def on_quit_action(self, *_args) -> None:
    """Triggered on user press `Ctrl + Q`"""
    self.quit()

  def do_shutdown(self) -> None:
    """Called on app closure. Proceeds all on exit operations"""
    Player().stop()
    if not Schema.get("root.settings.general.save-library"):
      logger.info("Resetting last library")
      Schema.set("root.state.library.last-library", "None")
    Schema._save()  # noqa: SLF001

    Constants.CACHE_FILE.seek(0)
    Constants.CACHE_FILE.truncate(0)
    yaml.dump(
      Constants.CACHE,
      Constants.CACHE_FILE,
      sort_keys=False,
      encoding="utf-8",
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


def main(_version) -> int:
  """App entrypoint"""
  init_logger()
  logger.info("Launching application")
  logger.info("OS: %s", sys.platform)

  # Cache is deprecated from v49
  if (Constants.DATA_DIR / "cache.yaml").exists():
    (Constants.DATA_DIR / "cache.yaml").unlink(missing_ok=True)

  Constants.APP = app = ChronographApplication()

  return app.run(sys.argv)
