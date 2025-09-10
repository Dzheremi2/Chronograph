"""Some functions without a specific grouping"""

import os
import re
from pathlib import Path
from typing import Optional


def get_common_directory(paths: tuple[str]) -> Optional[str]:
    """Return a common directory for provided paths or `None`.

    Parameters
    ----------
    paths : tuple[str]
        Paths to files

    Returns
    -------
    Optional[str]
        Common directory path or `None` if not in the same tree
    """
    dirs = [os.path.dirname(os.path.abspath(p)) for p in paths]
    common = os.path.commonpath(dirs)
    for p in dirs:
        if not Path(p).is_relative_to(Path(common)):
            return None
    return common


def is_lrc(text: str) -> bool:
    return bool(re.search(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]", text))
