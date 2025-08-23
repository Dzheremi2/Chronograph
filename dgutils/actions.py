import json
from functools import wraps

import yaml
from gi.repository import Gio, Gtk


class Actions:
    """Create Gio.SimpleAction(+shortcuts) from a GResource schema.

    Use via subclass (call `super().__init__(self, schema_dict)`) or as:

    ::

        @Actions.from_schema(".../actions.yaml")
        class MyWidget(...): ...
    """

    def __init__(self, instance, schema: dict):
        self.instance = instance
        self.schema = schema
        self._setup()

    def _setup(self):
        for group_name, actions in self.schema.get("groups", {}).items():
            action_group = Gio.SimpleActionGroup.new()
            shortcut_controller = Gtk.ShortcutController()
            has_shortcuts = False  # GTK may not expose get_shortcuts(); track ourselves

            for action in actions:
                name = action["name"]
                callback_name = action["callback"]
                callback = self._resolve_callback(callback_name)

                gio_action = Gio.SimpleAction.new(name, None)

                raw_args: list[str] = action.get("with_args", [])
                resolved_args = self._resolve_args(raw_args)

                if resolved_args:
                    gio_action.connect("activate", callback, *resolved_args)
                else:
                    gio_action.connect("activate", callback)

                action_group.add_action(gio_action)

                if shortcut := action.get("shortcut"):
                    shortcut_controller.add_shortcut(
                        Gtk.Shortcut.new(
                            trigger=Gtk.ShortcutTrigger.parse_string(shortcut),
                            action=Gtk.NamedAction.new(f"{group_name}.{name}"),
                        )
                    )
                    has_shortcuts = True

            self.instance.insert_action_group(group_name, action_group)
            if has_shortcuts:
                self.instance.add_controller(shortcut_controller)

    def _resolve_callback(self, dotted: str):
        parts = dotted.split(".")
        obj = self.instance
        if parts and parts[0] == "self":
            parts = parts[1:]
        for part in parts:
            obj = getattr(obj, part)
        return obj

    def _resolve_args(self, raw_args: list[str]):
        out = []
        for a in raw_args:
            if isinstance(a, str) and a.startswith("self."):
                out.append(self._resolve_attr_chain(self.instance, a[5:]))
            else:
                out.append(a)
        return out

    @staticmethod
    def _resolve_attr_chain(root, dotted: str):
        obj = root
        for part in dotted.split("."):
            obj = getattr(obj, part)
        return obj

    @classmethod
    def from_schema(cls, path: str, encoding: str = "yaml"):
        """Class decorator: load schema from GResource and build actions after `__init__`."""

        def class_decorator(target_cls):
            original_init = target_cls.__init__

            @wraps(original_init)
            def new_init(self, *args, **kwargs):
                # Run original constructor first
                original_init(self, *args, **kwargs)

                # Load schema from GResource
                gfile = Gio.File.new_for_uri(f"resource://{path}")
                contents = gfile.load_contents(None)[1].decode("utf-8")
                schema = (
                    yaml.safe_load(contents)
                    if encoding == "yaml"
                    else json.loads(contents)
                )

                # Build actions/shortcuts on this instance
                cls(self, schema)

            target_cls.__init__ = new_init
            return target_cls

        return class_decorator
