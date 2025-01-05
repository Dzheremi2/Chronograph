# gobject_signal.py
#
# Copyright 2022 James Westman <james@jwestman.net>
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

import typing as T

from .common import *
from .contexts import ScopeCtx
from .gtkbuilder_template import Template


class SignalFlag(AstNode):
    grammar = AnyOf(
        UseExact("flag", "swapped"),
        UseExact("flag", "not-swapped"),
        UseExact("flag", "after"),
    )

    @property
    def flag(self) -> str:
        return self.tokens["flag"]

    @validate()
    def unique(self):
        self.validate_unique_in_parent(
            f"Duplicate flag '{self.flag}'", lambda x: x.flag == self.flag
        )

    @validate()
    def swapped_exclusive(self):
        if self.flag in ["swapped", "not-swapped"]:
            self.validate_unique_in_parent(
                "'swapped' and 'not-swapped' flags cannot be used together",
                lambda x: x.flag in ["swapped", "not-swapped"],
            )

    @validate()
    def swapped_unnecessary(self):
        if self.flag == "not-swapped" and self.parent.object_id is None:
            raise CompileWarning(
                "'not-swapped' is the default for handlers that do not specify an object",
                actions=[CodeAction("Remove 'not-swapped' flag", "")],
            )
        elif self.flag == "swapped" and self.parent.object_id is not None:
            raise CompileWarning(
                "'swapped' is the default for handlers that specify an object",
                actions=[CodeAction("Remove 'swapped' flag", "")],
            )

    @docs()
    def ref_docs(self):
        return get_docs_section("Syntax Signal")


class Signal(AstNode):
    grammar = Statement(
        UseIdent("name"),
        Optional(
            [
                "::",
                UseIdent("detail_name").expected("a signal detail name"),
            ]
        ),
        Keyword("=>"),
        Mark("detail_start"),
        Optional(["$", UseLiteral("extern", True)]),
        UseIdent("handler").expected("the name of a function to handle the signal"),
        Match("(").expected("argument list"),
        Optional(UseIdent("object")).expected("object identifier"),
        Match(")").expected(),
        ZeroOrMore(SignalFlag),
        Mark("detail_end"),
    )

    @property
    def name(self) -> str:
        return self.tokens["name"]

    @property
    def detail_name(self) -> T.Optional[str]:
        return self.tokens["detail_name"]

    @property
    def full_name(self) -> str:
        if self.detail_name is None:
            return self.name
        else:
            return self.name + "::" + self.detail_name

    @property
    def handler(self) -> str:
        return self.tokens["handler"]

    @property
    def object_id(self) -> T.Optional[str]:
        return self.tokens["object"]

    @property
    def flags(self) -> T.List[SignalFlag]:
        return self.children[SignalFlag]

    # Returns True if the "swapped" flag is present, False if "not-swapped" is present, and None if neither are present.
    # GtkBuilder's default if swapped is not specified is to not swap the arguments if no object is specified, and to
    # swap them if an object is specified.
    @property
    def is_swapped(self) -> T.Optional[bool]:
        for flag in self.flags:
            if flag.flag == "swapped":
                return True
            elif flag.flag == "not-swapped":
                return False
        return None

    @property
    def is_after(self) -> bool:
        return any(x.flag == "after" for x in self.flags)

    @property
    def gir_signal(self) -> T.Optional[gir.Signal]:
        if self.gir_class is not None and not isinstance(self.gir_class, ExternType):
            return self.gir_class.signals.get(self.tokens["name"])
        else:
            return None

    @property
    def gir_class(self):
        return self.parent.parent.gir_class

    @property
    def document_symbol(self) -> DocumentSymbol:
        detail = self.ranges["detail_start", "detail_end"]
        return DocumentSymbol(
            self.full_name,
            SymbolKind.Event,
            self.range,
            self.group.tokens["name"].range,
            detail.text if detail is not None else None,
        )

    def get_reference(self, idx: int) -> T.Optional[LocationLink]:
        if self.object_id is not None and idx in self.group.tokens["object"].range:
            obj = self.context[ScopeCtx].objects.get(self.object_id)
            if obj is not None:
                return LocationLink(
                    self.group.tokens["object"].range, obj.range, obj.ranges["id"]
                )

        return None

    @validate("handler")
    def old_extern(self):
        if not self.tokens["extern"]:
            if self.handler is not None:
                raise UpgradeWarning(
                    "Use the '$' extern syntax introduced in blueprint 0.8.0",
                    actions=[CodeAction("Use '$' syntax", "$" + self.handler)],
                )

    @validate("name")
    def signal_exists(self):
        if self.gir_class is None or self.gir_class.incomplete:
            # Objects that we have no gir data on should not be validated
            # This happens for classes defined by the app itself
            return

        if self.gir_signal is None:
            raise CompileError(
                f"Class {self.gir_class.full_name} does not contain a signal called {self.tokens['name']}",
                did_you_mean=(self.tokens["name"], self.gir_class.signals.keys()),
            )

    @validate("object")
    def object_exists(self):
        object_id = self.tokens["object"]
        if object_id is None:
            return

        if self.context[ScopeCtx].objects.get(object_id) is None:
            raise CompileError(f"Could not find object with ID '{object_id}'")

    @validate("name")
    def deprecated(self) -> None:
        if self.gir_signal is not None and self.gir_signal.deprecated:
            hints = []
            if self.gir_signal.deprecated_doc:
                hints.append(self.gir_signal.deprecated_doc)
            raise DeprecatedWarning(
                f"{self.gir_signal.signature} is deprecated",
                hints=hints,
            )

    @docs("name")
    def signal_docs(self):
        if self.gir_signal is not None:
            return self.gir_signal.doc

    @docs("detail_name")
    def detail_docs(self):
        if self.name == "notify":
            if self.gir_class is not None and not isinstance(
                self.gir_class, ExternType
            ):
                prop = self.gir_class.properties.get(self.tokens["detail_name"])
                if prop is not None:
                    return prop.doc

    @docs("=>")
    def ref_docs(self):
        return get_docs_section("Syntax Signal")


@decompiler("signal")
def decompile_signal(ctx, gir, name, handler, swapped=None, after="false", object=None):
    object_name = object or ""
    name = name.replace("_", "-")
    line = f"{name} => ${handler}({object_name})"

    if decompile.truthy(swapped):
        line += " swapped"
    elif swapped is not None:
        line += " not-swapped"

    if decompile.truthy(after):
        line += " after"

    line += ";"
    ctx.print(line)
    return gir
