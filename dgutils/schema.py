import json
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from gi.repository import Gio, GObject

Transform = Callable[[Any], Any]


class Schema(GObject.GObject):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, (str, object))}

    def __init__(self, default_schema_resource: str, user_schema_path: Path) -> None:
        super().__init__()
        self._rules = self._load_yaml_from_resource(default_schema_resource)
        self._path = user_schema_path
        self._data = self._load_or_create_user_data(self._path)
        corrected, changed = self._apply_validation_and_cleanup(self._data, self._rules)
        self._data = corrected
        if changed:
            self._save()

    def get(self, dotted_path: str) -> Any:
        """Returns a value assigned to a given schema keypath

        Parameters
        ----------
        dotted_path : str
            path.to.the.key

        Returns
        -------
        Any
            Value of the keypath
        """
        node, key = self._resolve_parent_and_key(self._data, dotted_path)
        return node[key]

    def set(self, dotted_path: str, value: Any) -> None:
        """Sets a given value to a given keypath

        Parameters
        ----------
        dotted_path : str
            path.to.the.key
        value : Any
            Value
        """
        valid_value = self._validate_single_value(dotted_path, value)
        node, key = self._resolve_parent_and_key(self._data, dotted_path)
        if node.get(key) != valid_value:
            node[key] = valid_value
            self._save()
            self.emit("changed", dotted_path, valid_value)

    def bind(
        self,
        dotted_path: str,
        target: GObject.Object,
        prop: str,
        *,
        bidirectional: bool = True,
        sync_create: bool = True,
        transform_to: Optional[Transform] = None,
        transform_from: Optional[Transform] = None,
        preserve_cursor: bool = False,
    ):
        """Bounds given keypath to a given GObject.Object property

        Parameters
        ----------
        dotted_path : str
            path.to.the.key
        target : GObject.Object
            Target GObject
        prop : str
            Property name on target GObject
        bidirectional : bool, optional
            Should the sync be bidirectional, by default True
        sync_create : bool, optional
            Should widget be synced with the value on bind, by default True
        transform_to : Optional[Transform], optional
            A transform method for `schema -> gobject` operation, by default None
        transform_from : Optional[Transform], optional
            A transform method for `gobject -> schema` operations, by default None
        preserve_cursor : bool, optional
            Protects cursor from being reset for text input widgets. Disables widget reflections on schema outside-of-binding changes. By default False

        Returns
        -------
        Binding | None
            If preserve_cursor not used, returns a `Binding` object with `unbind()` method

        Raises
        ------
        AttributeError
            Raised if target GObject doesn't have provided property
        """
        if target.find_property(prop) is None:
            raise AttributeError(
                f"{type(target).__name__} has no GObject property '{prop}'"
            )

        if sync_create:
            value = self.get(dotted_path)
            if transform_to:
                value = transform_to(value)
            target.set_property(prop, value)

        def on_schema_changed(_schema, changed_key: str, value: Any):
            if changed_key != dotted_path:
                return
            if transform_to:
                value = transform_to(value)
            target.set_property(prop, value)

        if not preserve_cursor:
            handler_schema = self.connect("changed", on_schema_changed)

        handler_widget = None
        if bidirectional:

            def on_widget_notify(_obj, _pspec):
                wvalue = target.get_property(prop)
                if transform_from:
                    wvalue = transform_from(wvalue)
                self.set(dotted_path, wvalue)

            handler_widget = target.connect(f"notify::{prop}", on_widget_notify)

        if not preserve_cursor:

            class Binding:
                def unbind(_self):  # pylint: disable=no-self-argument
                    self.disconnect(handler_schema)
                    if handler_widget:
                        target.disconnect(handler_widget)

            return Binding()

    @staticmethod
    def _load_yaml_from_resource(resource_path: str) -> dict[str, Any]:
        gfile = Gio.File.new_for_uri(f"resource://{resource_path}")
        _, contents, __ = gfile.load_contents(None)
        return yaml.safe_load(contents.decode()) or {}

    def _load_or_create_user_data(self, path: Path) -> dict[str, Any]:
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        path.parent.mkdir(parents=True, exist_ok=True)
        return {}

    def _save(self) -> None:
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def _apply_validation_and_cleanup(
        self, user_data: dict[str, Any], rules: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        changed = False

        def walk(
            rule_node: dict[str, Any], data_node: dict[str, Any]
        ) -> dict[str, Any]:
            nonlocal changed
            corrected: dict[str, Any] = {}

            for name, rule in rule_node.items():
                if _is_leaf_rule(rule):
                    # leaf setting with constraints
                    value = data_node.get(name, rule.get("default"))
                    valid_value, was_changed = self._validate_leaf(rule, value)
                    if was_changed:
                        changed = True
                    corrected[name] = valid_value
                else:
                    # nested group
                    child_data = data_node.get(name, {})
                    if not isinstance(child_data, dict):
                        child_data = {}
                        changed = True
                    corrected[name] = walk(rule, child_data)

            for _extra in data_node.keys() - rule_node.keys():
                changed = True  # cleanup
            return corrected

        corrected_root = walk(rules, user_data if isinstance(user_data, dict) else {})
        return corrected_root, changed

    def _validate_leaf(self, rule: dict[str, Any], value: Any) -> tuple[Any, bool]:
        expected_type = rule.get("type")
        default_value = rule.get("default")
        changed = False

        pytype = {"int": int, "str": str, "bool": bool, "float": float}.get(
            expected_type, type(default_value)
        )
        if not isinstance(value, pytype):
            value = default_value
            changed = True

        if expected_type in ("int", "float"):
            if "min" in rule and value < rule["min"]:
                value = default_value
                changed = True
            if "max" in rule and value > rule["max"]:
                value = default_value
                changed = True

        if "enum" in rule and value not in rule["enum"]:
            value = default_value
            changed = True

        return value, changed

    def _validate_single_value(self, dotted_path: str, value: Any) -> Any:
        rule_node, key = self._resolve_parent_and_key(self._rules, dotted_path)
        rule = rule_node[key]
        validated, _ = self._validate_leaf(rule, value)
        return validated

    @staticmethod
    def _resolve_parent_and_key(
        root: dict[str, Any], dotted_path: str
    ) -> tuple[dict[str, Any], str]:
        parts = dotted_path.split(".")
        if not parts:
            raise KeyError("Empty dotted path")

        node = root
        for name in parts[:-1]:
            node = node[name]
            if not isinstance(node, dict):
                raise KeyError(
                    f"Non-group node encountered at '{name}' within '{dotted_path}'"
                )
        return node, parts[-1]


def _is_leaf_rule(rule: Any) -> bool:
    return isinstance(rule, dict) and ("type" in rule)
