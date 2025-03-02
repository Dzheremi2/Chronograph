import os

import yaml
from gi.repository import Adw

from chronograph import shared


def save_location(*_args) -> None:
    """Saves currently opened direcotry to the saves"""
    if len(shared.cache["pins"]) == 0:
        print("Triggered len method")
        entry: dict = {
            "path": shared.state_schema.get_string("opened-dir"),
            "name": os.path.basename(shared.state_schema.get_string("opened-dir")[:-1]),
        }

        shared.cache["pins"].append(entry)
        shared.cache_file.seek(0)
        yaml.dump(
            shared.cache,
            shared.cache_file,
            sort_keys=False,
            encoding=None,
            allow_unicode=True,
        )
        shared.win.build_sidebar()
    else:
        print("Triggered multiple method")
        entry: dict = {
            "path": shared.state_schema.get_string("opened-dir"),
            "name": os.path.basename(shared.state_schema.get_string("opened-dir")[:-1]),
        }

        shared.cache["pins"].append(entry)
        shared.cache_file.seek(0)
        yaml.dump(
            shared.cache,
            shared.cache_file,
            sort_keys=False,
            encoding=None,
            allow_unicode=True,
        )
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Directory saved successfully"))
        )
        shared.win.build_sidebar()
    shared.win.add_dir_to_saves_button.set_visible(False)
