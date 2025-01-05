# annotations.py
#
# Copyright 2024 James Westman <james@jwestman.net>
#
# This file is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This file is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: LGPL-3.0-or-later

# Extra information about types in common libraries that's used for things like completions.

import typing as T
from dataclasses import dataclass

from . import gir


@dataclass
class Annotation:
    translatable_properties: T.List[str]


def is_property_translated(property: gir.Property):
    ns = property.get_containing(gir.Namespace)
    ns_name = ns.name + "-" + ns.version
    if annotation := _ANNOTATIONS.get(ns_name):
        assert property.container is not None
        return (
            property.container.name + ":" + property.name
            in annotation.translatable_properties
        )
    else:
        return False


_ANNOTATIONS = {
    "Gtk-4.0": Annotation(
        translatable_properties=[
            "AboutDialog:comments",
            "AboutDialog:translator-credits",
            "AboutDialog:website-label",
            "AlertDialog:detail",
            "AlertDialog:message",
            "AppChooserButton:heading",
            "AppChooserDialog:heading",
            "AppChooserWidget:default-text",
            "AssistantPage:title",
            "Button:label",
            "CellRendererText:markup",
            "CellRendererText:placeholder-text",
            "CellRendererText:text",
            "CheckButton:label",
            "ColorButton:title",
            "ColorDialog:title",
            "ColumnViewColumn:title",
            "ColumnViewRow:accessible-description",
            "ColumnViewRow:accessible-label",
            "Entry:placeholder-text",
            "Entry:primary-icon-tooltip-markup",
            "Entry:primary-icon-tooltip-text",
            "Entry:secondary-icon-tooltip-markup",
            "Entry:secondary-icon-tooltip-text",
            "EntryBuffer:text",
            "Expander:label",
            "FileChooserNative:accept-label",
            "FileChooserNative:cancel-label",
            "FileChooserWidget:subtitle",
            "FileDialog:accept-label",
            "FileDialog:title",
            "FileDialog:initial-name",
            "FileFilter:name",
            "FontButton:title",
            "FontDialog:title",
            "Frame:label",
            "Inscription:markup",
            "Inscription:text",
            "Label:label",
            "ListItem:accessible-description",
            "ListItem:accessible-label",
            "LockButton:text-lock",
            "LockButton:text-unlock",
            "LockButton:tooltip-lock",
            "LockButton:tooltip-not-authorized",
            "LockButton:tooltip-unlock",
            "MenuButton:label",
            "MessageDialog:secondary-text",
            "MessageDialog:text",
            "NativeDialog:title",
            "NotebookPage:menu-label",
            "NotebookPage:tab-label",
            "PasswordEntry:placeholder-text",
            "Picture:alternative-text",
            "PrintDialog:accept-label",
            "PrintDialog:title",
            "Printer:name",
            "PrintJob:title",
            "PrintOperation:custom-tab-label",
            "PrintOperation:export-filename",
            "PrintOperation:job-name",
            "ProgressBar:text",
            "SearchEntry:placeholder-text",
            "ShortcutLabel:disabled-text",
            "ShortcutsGroup:title",
            "ShortcutsSection:title",
            "ShortcutsShortcut:title",
            "ShortcutsShortcut:subtitle",
            "StackPage:title",
            "Text:placeholder-text",
            "TextBuffer:text",
            "TreeViewColumn:title",
            "Widget:tooltip-markup",
            "Widget:tooltip-text",
            "Window:title",
            "Editable:text",
            "FontChooser:preview-text",
        ]
    ),
    "Adw-1": Annotation(
        translatable_properties=[
            "AboutDialog:comments",
            "AboutDialog:translator-credits",
            "AboutWindow:comments",
            "AboutWindow:translator-credits",
            "ActionRow:subtitle",
            "ActionRow:title",
            "AlertDialog:body",
            "AlertDialog:heading",
            "Avatar:text",
            "Banner:button-label",
            "Banner:title",
            "ButtonContent:label",
            "Dialog:title",
            "ExpanderRow:subtitle",
            "MessageDialog:body",
            "MessageDialog:heading",
            "NavigationPage:title",
            "PreferencesGroup:description",
            "PreferencesGroup:title",
            "PreferencesPage:description",
            "PreferencesPage:title",
            "PreferencesRow:title",
            "SplitButton:dropdown-tooltip",
            "SplitButton:label",
            "StatusPage:description",
            "StatusPage:title",
            "TabPage:indicator-tooltip",
            "TabPage:keyword",
            "TabPage:title",
            "Toast:button-label",
            "Toast:title",
            "ViewStackPage:title",
            "ViewSwitcherTitle:subtitle",
            "ViewSwitcherTitle:title",
            "WindowTitle:subtitle",
            "WindowTitle:title",
        ]
    ),
    "Shumate-1.0": Annotation(
        translatable_properties=[
            "License:extra-text",
            "MapSource:license",
            "MapSource:name",
        ]
    ),
    "GtkSource-5": Annotation(
        translatable_properties=[
            "CompletionCell:markup",
            "CompletionCell:text",
            "CompletionSnippets:title",
            "CompletionWords:title",
            "GutterRendererText:markup",
            "GutterRendererText:text",
            "SearchSettings:search-text",
            "Snippet:description",
            "Snippet:name",
            "SnippetChunk:tooltip-text",
            "StyleScheme:description",
            "StyleScheme:name",
        ]
    ),
}
