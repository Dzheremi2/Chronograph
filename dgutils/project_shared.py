import builtins
import importlib
import json
from pathlib import Path

import yaml
from gi.repository import Gio, GObject


class AbstractSchema:
    """An abstract class to allow IDE static analysis hint for `bind()` method"""

    def bind(self, key: str, gobject: GObject.Object, prop: str) -> None:
        """Bind provided schema key' value to a provided GObject' value

        Parameters
        ----------
        key : str
            Key of the Schema value
        object : GObject.Object
            A GObject which' property is going to be bound
        prop : str
            Property name `!MUST BE A GObject.Property!`
        """


def validate_schema(data: dict, schema_def: dict) -> tuple[dict, bool]:
    result = {}
    changed = False

    for key, rule in schema_def.items():
        expected_type = rule.get("type")
        default = rule.get("default")
        value = data.get(key, default)

        pytype = {"int": int, "str": str, "bool": bool, "float": float}.get(
            expected_type, str
        )
        valid = isinstance(value, pytype)

        if expected_type in ("int", "float"):
            if "min" in rule and value < rule["min"]:
                valid = False
            if "max" in rule and value > rule["max"]:
                valid = False

        if "enum" in rule and value not in rule["enum"]:
            valid = False

        if not valid:
            value = default
            changed = True

        result[key] = value

    return result, changed


# pylint: disable=invalid-name
class ProjectShared:
    Constants: type
    Schema: object

    def __init__(
        self, constants_resource: str, schema_resource: str, schema_path: Path
    ):
        self.constants_data = self._load_yaml_resource(constants_resource)
        self.schema_def = self._load_yaml_resource(schema_resource)
        self.Constants = self._generate_constants(self.constants_data)
        self.Schema: AbstractSchema = self._generate_schema(
            self.schema_def, schema_path
        )

    def _load_yaml_resource(self, resource_path: str) -> dict:
        file = Gio.File.new_for_uri(f"resource://{resource_path}")
        _, contents, __ = file.load_contents(None)
        return yaml.safe_load(contents.decode())

    def _generate_constants(self, consts: dict):
        py_encoded = consts.pop("PyEncStr", {})
        py_imports = consts.pop("PyEncImports", [])

        class Constants:
            pass

        for k, v in consts.items():
            setattr(Constants, k, v)

        eval_context = {"Constants": Constants}
        for name in py_imports:
            if ":" in name:
                module_name, attr_name = name.split(":")
                module = importlib.import_module(module_name)
                eval_context[attr_name] = getattr(module, attr_name)
            else:
                module = importlib.import_module(name)
                eval_context[name.split(".")[-1]] = module

        for k, expr in py_encoded.items():
            try:
                # pylint: disable=eval-used
                value = eval(expr, {**eval_context, **vars(builtins)})
                setattr(Constants, k, value)
            except Exception as e:
                raise RuntimeError(f"PyEncStr error in {k}: {expr}\n{e}") from e

        return Constants

    def _generate_schema(self, schema_def: dict, schema_path: Path):
        class Schema(GObject.GObject):
            __gsignals__ = {
                "changed": (GObject.SignalFlags.RUN_FIRST, None, (str, object))
            }

            def __init__(self, file_path, defaults):
                super().__init__()
                self._file: Path = file_path
                self._schema_def = defaults

                if file_path.exists():
                    with file_path.open("r", encoding="utf-8") as f:
                        user_data = json.load(f)
                else:
                    self._file.parent.mkdir(parents=True, exist_ok=True)
                    user_data = {}

                validated, changed = validate_schema(user_data, defaults)
                self._data = validated
                if changed or user_data != validated:
                    self._save()

            def get(self, key):
                return self._data[key]

            def set(self, key, value):
                if self._data.get(key) != value:
                    self._data[key] = value
                    self._save()
                    self.emit("changed", key, value)

            def _set(self, key, value):
                if self._data.get(key) != value:
                    self._data[key] = value
                    self._save()

            def _save(self):
                with self._file.open("w+", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)

            def bind(self, key: str, gobject: GObject.Object, prop: str):
                """Bind provided schema key' value to a provided GObject' value

                Parameters
                ----------
                key : str
                    Key of the Schema value
                object : GObject.Object
                    A GObject which' property is going to be bound
                prop : str
                    Property name `!MUST BE A GObject.Property!`
                """
                gobject.set_property(prop, self.get(key))

                def on_changed(_, k, v):
                    if k == key:
                        gobject.set_property(prop, v)

                self.connect("changed", on_changed)

                def on_widget_change(w, _):
                    self._set(key, w.get_property(prop))

                gobject.connect(f"notify::{prop}", on_widget_change)

        schema = Schema(schema_path, schema_def)

        for key in schema_def.keys():
            gname = key.replace("-", "_")
            setattr(Schema, f"get_{gname}", lambda self, k=key: self.get(k))
            setattr(Schema, f"set_{gname}", lambda self, v, k=key: self.set(k, v))

        return schema
