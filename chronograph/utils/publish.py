import hashlib
import re
from binascii import unhexlify

import requests
from gi.repository import Adw

from chronograph import shared
from chronograph.utils.parsers import sync_lines_parser


def verify_nonce(result, target) -> bool:
    """Checks if current nonce is valid

    Returns
    -------
    bool
        validity
    """
    if len(result) != len(target):
        return False

    for i in range(len(result)):
        if result[i] > target[i]:
            return False
        elif result[i] < target[i]:
            break

    return True


def solve_challenge(prefix, target_hex) -> str:
    """Generates nonce for publishing

    Returns
    -------
    str
        generated noce
    """
    target = unhexlify(target_hex.upper())
    nonce = 0

    while True:
        input_data = f"{prefix}{nonce}".encode()
        hashed = hashlib.sha256(input_data).digest()

        if verify_nonce(hashed, target):
            break
        else:
            nonce += 1

    return str(nonce)


def make_plain_lyrics(lyrics: str) -> str:
    """Generates plain lyrics form `chronograph.ChronographWindow.sync_lines`

    Returns
    -------
    str
        plain lyrics
    """
    pattern = r"\[.*?\] "
    lyrics = lyrics.splitlines()
    plain_lyrics = []
    for line in plain_lyrics:
        plain_lyrics.append(re.sub(pattern, "", line))
    return "\n".join(plain_lyrics[:-1])


def do_publish(title: str, artist: str, album: str, duration: int, lyrics: str) -> None:
    challenge_data = requests.post(url="https://lrclib.net/api/request-challenge")
    challenge_data = challenge_data.json()
    nonce = solve_challenge(
        prefix=challenge_data["prefix"], target_hex=challenge_data["target"]
    )
    print(f"X-Publish-Token: {challenge_data['prefix']}:{nonce}")
    response: requests.Response = requests.post(
        url="https://lrclib.net/api/publish",
        headers={
            "X-Publish-Token": f"{challenge_data['prefix']}:{nonce}",
            "Content-Type": "application/json",
        },
        params={"keep_headers": "true"},
        json={
            "trackName": title,
            "artistName": artist,
            "albumName": album,
            "duration": duration,
            "plainLyrics": make_plain_lyrics(lyrics),
            "syncedLyrics": lyrics,
        },
    )

    if response.status_code == 201:
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Published successfully: ") + str(response.status_code))
        )
        shared.win.lrclib_manual_toast_overlay.add_toast(
            Adw.Toast(title=_("Published successfully: ") + str(response.status_code))
        )
    elif response.status_code == 400:
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Incorrect publish token: ") + str(response.status_code))
        )
        shared.win.lrclib_manual_toast_overlay.add_toast(
            Adw.Toast(title=_("Incorrect publish token: ") + str(response.status_code))
        )
    else:
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Unknown error occured: ") + str(response.status_code))
        )
        shared.win.lrclib_manual_toast_overlay.add_toast(
            Adw.Toast(title=_("Unknown error occured: ") + str(response.status_code))
        )

    shared.win.export_lyrics_button.set_icon_name("export-to-symbolic")
    shared.win.lrclib_manual_publish_button.set_label(_("Publish"))
