# window.py
#
# Copyright 2024 Dzheremi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw
from gi.repository import Gtk
from .noDirSelectedGreeting import noDirSelectedGreeting
from .songCard import songCard


@Gtk.Template(resource_path='/com/github/dzheremi/lrcmake/gtk/window.ui')
class LrcmakeWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'LrcmakeWindow'

    music_lib = Gtk.Template.Child()
    nav_view = Gtk.Template.Child()
    syncing = Gtk.Template.Child()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.music_lib.get_child_at_index(0) == None:
            self.music_lib.set_property('halign', 'center')
            self.music_lib.set_property('valign', 'center')
            self.music_lib.set_property('homogeneous', False)
            self.music_lib.append(noDirSelectedGreeting())
