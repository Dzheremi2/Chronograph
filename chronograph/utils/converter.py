"""Converters for timestamps"""

import re

from chronograph.internal import Schema


def mcs_to_timestamp(mcs: int) -> str:
    """Convert microseconds to timestamp format"""
    ms = mcs // 1000  # get milliseconds
    match Schema.get_precise_milliseconds():
        case True:
            return f"[{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{ms % 1000:03d}] "
        case False:
            milliseconds = f"{ms % 1000:03d}"
            return (
                f"[{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{milliseconds[:-1]}] "
            )


def timestamp_to_mcs(text: str) -> int:
    """Convert timestamp format to microseconds"""
    pattern = r"\[([^\[\]]+)\]"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"No timestamp found in text: {text}")
    timestamp = match[0]
    pattern = r"(\d+):(\d+).(\d+)"
    mm, ss, ms = re.search(pattern, timestamp).groups()
    if len(ms) == 2:
        ms = ms + "0"
    total_ss = int(mm) * 60 + int(ss)
    total_ms = total_ss * 1000 + int(ms)
    return total_ms * 1000
