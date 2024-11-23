import sys
import gi
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, Gdk
from .window import LrcmakeWindow
from .selectData import select_file, select_dir, select_lyrics_file
from .parsers import clipboard_parser
from .exportData import export_clipboard
from .publish import do_publish
from . import shared

class LrcmakeApplication(Adw.Application):
    def __init__(self):
        # Create basic actions and resources
        super().__init__(application_id=shared.APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('select_file', select_file, ['<primary>o'])
        self.create_action('select_dir', select_dir, ['<primary><shift>o'])
        self.create_action('read_from_clipboard', clipboard_parser)
        self.create_action('read_from_file', select_lyrics_file)
        self.create_action('export_to_clipboard', export_clipboard)
        self.create_action("export_to_lrclib", self.async_do_publish)
        self.create_action('about_app', self.show_about_dialog)
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_resource_path(shared.PREFIX + "/data/icons")

    # Emmits when app is activated
    def do_activate(self):
        win = self.props.active_window
        if not win:
            shared.win = win = LrcmakeWindow(application=self)
        shared.win.present()

    # Used for creating new actions
    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    # Creates thread for publishing on LRCLIB
    def async_do_publish(self, *args):
        thread = threading.Thread(target=do_publish)
        thread.daemon = True
        thread.start()
        shared.win.export_lyrics.set_child(Gtk.Spinner(spinning=True))

    # Shows About App dialog
    def show_about_dialog(self, *args):
        dialog = Adw.AboutDialog.new_from_appdata(shared.PREFIX + "/" + shared.APP_ID + ".metainfo.xml", shared.VERSION)
        dialog.set_version(shared.VERSION)
        dialog.set_developers(
            (
                "Dzheremi https://github.com/Dzheremi2",
            )
        )
        dialog.set_designers(("Dzheremi",))
        dialog.set_translator_credits(_("Thanks for all translators on Hosted Weblate! https://hosted.weblate.org/projects/lrcmake/lrcmake/"))
        dialog.set_copyright("© 2024 Dzheremi")
        dialog.add_legal_section(
            "LRClib",
            "",
            Gtk.License.MIT_X11
        )
        dialog.present(shared.win)

# App's Entry point
def main(_version):
    print(shared.PREFIX)
    shared.app = app = LrcmakeApplication()
    return app.run(sys.argv)