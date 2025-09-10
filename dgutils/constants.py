import builtins
import importlib
from typing import Any, Dict

import yaml
from gi.repository import Gio


class Constants:
    @classmethod
    def from_resource(cls, resource_path: str) -> "Constants":
        data = cls._load_yaml_from_resource(resource_path)
        instance = cls()
        instance._populate_from_data(data)
        return instance

    @staticmethod
    def _load_yaml_from_resource(resource_path: str) -> Dict[str, Any]:
        gfile = Gio.File.new_for_uri(f"resource://{resource_path}")
        __, contents, _ = gfile.load_contents(None)
        return yaml.safe_load(contents.decode()) or {}

    def _populate_from_data(self, data: Dict[str, Any]) -> None:
        py_encoded = data.pop("PyEncStr", {}) or {}
        py_imports = data.pop("PyEncImports", []) or []

        for key, value in data.items():
            setattr(self, key, value)

        eval_context: Dict[str, Any] = {"Constants": self, **vars(builtins)}
        for item in py_imports:
            if ":" in item:
                module_name, attr_name = item.split(":", 1)
                module = importlib.import_module(module_name)
                eval_context[attr_name] = getattr(module, attr_name)
            else:
                module = importlib.import_module(item)
                eval_context[item.split(".")[-1]] = module

        for key, expr in py_encoded.items():
            try:
                # pylint: disable=eval-used
                value = eval(expr, eval_context)
            except Exception as exc:
                raise RuntimeError(
                    f"PyEncStr evaluation failed for '{key}': {expr}\n{exc}"
                ) from exc
            setattr(self, key, value)
