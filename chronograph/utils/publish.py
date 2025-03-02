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


def make_plain_lyrics() -> str:
    """Generates plain lyrics form `chronograph.ChronographWindow.sync_lines`

    Returns
    -------
    str
        plain lyrics
    """
    pattern = r"\[.*?\] "
    plain_lyrics = []
    for child in shared.win.sync_lines:
        plain_lyrics.append(re.sub(pattern, "", child.get_text()))
    return "\n".join(plain_lyrics[:-1])


def do_publish() -> None:
    """Publishes lyrics to LRClib

    Raises
    ------
    AttributeError
        raised if any needed property is \"Unknown\"

    needed properties: ::

        title: str
        artist: str
        album: str
    """
    if (
        shared.win.loaded_card._file.title is None
        or shared.win.loaded_card._file.title == ""
        or shared.win.loaded_card._file.artist is None
        or shared.win.loaded_card._file.artist == ""
        or shared.win.loaded_card._file.album is None
        or shared.win.loaded_card._file.album == ""
    ):
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Some of Title, Artist and/or Album fields are Unknown!"))
        )
        shared.win.export_lyrics_button.set_icon_name("export-to-symbolic")
        raise AttributeError('Some of Title, Artist and/or Album fields are "Unknown"')

    challenge_data = requests.post(url="https://lrclib.net/api/request-challenge")
    challenge_data = challenge_data.json()
    nonce = solve_challenge(
        prefix=challenge_data["prefix"], target_hex=challenge_data["target"]
    )
    print(f"X-Publish-Token: {challenge_data['prefix']}:{nonce}")
    response = requests.post(
        url="https://lrclib.net/api/publish",
        headers={
            "X-Publish-Token": f"{challenge_data['prefix']}:{nonce}",
            "Content-Type": "application/json",
        },
        params={"keep_headers": "true"},
        json={
            "trackName": shared.win.loaded_card.title,
            "artistName": shared.win.loaded_card.artist,
            "albumName": shared.win.loaded_card.album,
            "duration": shared.win.loaded_card.duration,
            "plainLyrics": make_plain_lyrics(),
            "syncedLyrics": sync_lines_parser(),
        },
    )

    if response.status_code == 201:
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Published successfully: ") + str(response.status_code))
        )
    elif response.status_code == 400:
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Incorrect publish token: ") + str(response.status_code))
        )
    else:
        shared.win.toast_overlay.add_toast(
            Adw.Toast(title=_("Unknown error occured: ") + str(response.status_code))
        )

    shared.win.export_lyrics_button.set_icon_name("export-to-symbolic")
