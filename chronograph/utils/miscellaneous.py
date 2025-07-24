"""Some functions without a specific grouping"""

import os
from pathlib import Path
from typing import Optional


def get_common_directory(paths: tuple[str]) -> Optional[str]:
    dirs = [os.path.dirname(os.path.abspath(p)) for p in paths]
    common = os.path.commonpath(dirs)
    for p in dirs:
        if not Path(p).is_relative_to(Path(common)):
            return None
    return common
