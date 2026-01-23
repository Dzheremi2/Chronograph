import asyncio
import contextlib
import re
import threading
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Callable, Iterable, Optional, Sized, cast

import httpx
import requests
from gi.repository import GLib, GObject

from chronograph.backend.media import BaseFile
from chronograph.internal import Constants, Schema
from dgutils import GSingleton
from dgutils.typing import unwrap

from . import APP_SIGNATURE_HEADER
from .cryptograpic_challenge import solve_challenge
from .exceptions import (
  APIRequestError,
  LRClibException,
  PublishAlreadyRunning,
  SearchEmptyReturn,
  TrackNotFound,
)
from .responses import LRClibChallenge, LRClibEntry

logger = Constants.LRCLIB_LOGGER


class Endpoints(StrEnum):
  GET = "https://lrclib.net/api/get"
  SEARCH = "https://lrclib.net/api/search"
  PUBLISH = "https://lrclib.net/api/publish"
  CHALLENGE = "https://lrclib.net/api/request-challenge"


class FetchStates(GObject.GEnum):
  PENDING = 0
  FAILED = 1
  CANCELLED = 2
  DONE = 3


class LRClibService(GObject.Object, metaclass=GSingleton):
  __gsignals__ = {
    "publish-done": (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # status-code
    "publish-failed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),  # Exception
    # Fetch-related signals
    "fetch-started": (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # path
    "fetch-state": (
      GObject.SignalFlags.RUN_FIRST,
      None,
      (
        str,
        FetchStates,
        object,
      ),  # path, FetchStates, Optional[Union[LRClibEntry, Exception]]
    ),
    "fetch-message": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # path, msg
    "fetch-all-done": (GObject.SignalFlags.RUN_FIRST, None, ()),
  }

  def __init__(self) -> None:
    super().__init__()
    self._is_publish_running = False

  async def api_get(self, track: BaseFile) -> LRClibEntry:
    """Does one track search by absolute metadata (any deviation will result in TrackNotFound)

    Parameters
    ----------
    track : BaseFile
      A track media file

    Returns
    -------
    LRClibEntry
      Dataclass instance will all attributes LRClib provide

    Raises
    ------
    TrackNotFound
      Raised if LRClib returned 404
    APIRequestError
      Raise on any other exception
    """
    async with httpx.AsyncClient() as client:
      try:
        params = {
          "track_name": track.title,
          "artist_name": track.artist,
          "album_name": track.album,
          "duration": track.duration,
        }
        response = await client.get(
          Endpoints.GET.value,
          params=params,
          headers={"User-Agent": APP_SIGNATURE_HEADER},
          timeout=10,
        )
        if response.status_code in (404, 400):
          logger.info("[GET] No entry for %s -- %s found", track.title, track.artist)
          raise TrackNotFound(f"No entry for {track.title} -- {track.artist} found")  # noqa: TRY301

        response.raise_for_status()

        data = response.json()
        return LRClibEntry(
          data["id"],
          data["trackName"],
          data["artistName"],
          data["albumName"],
          int(data["duration"]),
          data["instrumental"],
          data["plainLyrics"],
          data["syncedLyrics"],
        )
      # This re-raise mess is hapening since we need to catch all errors except those
      # directly related to LRClib
      except LRClibException:
        raise
      except httpx.RequestError as e:
        logger.exception("[GET] Network failure while fetching LRClib")
        raise APIRequestError(f"Network error: {e!s}") from e
      except httpx.HTTPStatusError as e:
        logger.exception("[GET] Non-200 nor 404 response")
        raise APIRequestError(f"Bad response: {e.response.status_code}") from e
      except Exception as e:
        logger.exception("[GET] Unexpected error")
        raise APIRequestError(f"Unexpected error: {type(e).__name__}: {e!s}") from e

  async def api_search(
    self, title: str, artist: str = "", album: str = ""
  ) -> Iterable[LRClibEntry]:
    """Does search on LRClib for provided track. Unlike get, this can return something
    even if data deviates from one on LRClib

    Parameters
    ----------
    track : BaseFile
      A track media file

    Returns
    -------
    Iterable[LRClibEntry]
      Iterable with LRClibEntry dataclasses representing all track found. Max of 20
      (API limitation)

    Raises
    ------
    SearchEmptyReturn
      Raised if no results dfound found for the request
    APIRequestError
      Raised on any other exception
    """  # noqa: D205
    async with httpx.AsyncClient() as client:
      try:
        params = {
          "track_name": title.strip() if title else "",
          "artist_name": artist.strip() if artist else "",
          "album_name": album.strip() if album else "",
        }
        response = await client.get(
          Endpoints.SEARCH.value,
          params=params,
          headers={"User-Agent": APP_SIGNATURE_HEADER},
        )
        response.raise_for_status()
        data = response.json()
        if data:
          tracks = []
          for item in data:
            track_ = LRClibEntry(
              item["id"],
              item["trackName"],
              item["artistName"],
              item["albumName"],
              int(item["duration"]),
              item["instrumental"],
              item["plainLyrics"],
              item["syncedLyrics"],
            )
            tracks.append(track_)
          logger.info("[SEARCH] Done for %s -- %s positively", title, artist)
          return tracks
        raise SearchEmptyReturn(f"No entries found for {title} -- {artist}")  # noqa: TRY301
      # This re-raise mess is hapening since we need to catch all errors except those
      # directly related to LRClib
      except LRClibException:
        raise
      except httpx.RequestError as e:
        logger.exception("[SEARCH] Network failure while fetching LRClib")
        raise APIRequestError(f"Network error: {e!s}") from e
      except httpx.HTTPStatusError as e:
        logger.exception("[SEARCH] Non-200 response")
        raise APIRequestError(f"Bad response: {e.response.status_code}") from e
      except Exception as e:
        logger.exception("[SEARCH] Unexpected error")
        raise APIRequestError(f"Unexpected error: {type(e).__name__}: {e!s}") from e

  async def api_challenge(self) -> LRClibChallenge:
    """Does cryptographic proof-of-work challenge request for publishing

    Returns
    -------
    LRClibChallenge
      Dataclass with `prefix` and `target` attributes

    Raises
    ------
    APIRequestError
      Raised on any exception
    """
    async with httpx.AsyncClient() as client:
      try:
        logger.info("[CHALLENGE] Requesting challenge from LRClib")
        response = await client.post(
          Endpoints.CHALLENGE.value, headers={"User-Agent": APP_SIGNATURE_HEADER}
        )
        response.raise_for_status()
        data = response.json()
        return LRClibChallenge(data["prefix"], data["target"])
      except httpx.RequestError as e:
        logger.exception("[CHALLENGE] Network failure while fetching LRClib")
        raise APIRequestError(f"Network error: {e!s}") from e
      except httpx.HTTPStatusError as e:
        logger.exception("[CHALLENGE] Non-200 response")
        raise APIRequestError(f"Bad response: {e.response.status_code}") from e
      except Exception as e:
        logger.exception("[CHALLENGE] Unexpected error")
        raise APIRequestError(f"Unexpected error: {type(e).__name__}: {e!s}") from e

  def publish(
    self,
    track: BaseFile,
    plain_lyrics: str,
    synced_lyrics: str,
  ) -> None:
    """Publishes the given lyrics to LRClib for a given track

    Parameters
    ----------
    track : BaseFile
      A track media file
    plain_lyrics : str
      Plain lyrics
    synced_lyrics : str
      Synced lyrics
    """

    def do_publish(
      title: str,
      artist: str,
      album: str,
      duration: int,
      plain_lyrics: str,
      synced_lyrics: str,
    ) -> None:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)

      try:
        challenge = loop.run_until_complete(self.api_challenge())
      except Exception as e:
        self._is_publish_running = False
        GLib.idle_add(self.emit, "publish-failed", e)
      finally:
        loop.close()

      nonce = solve_challenge(challenge.prefix, challenge.target)
      logger.info("X-Publish-Token: %s", f"{challenge.target}:{nonce}")

      try:
        response: requests.Response = requests.post(
          Endpoints.PUBLISH.value,
          headers={
            "X-Publish-Token": f"{challenge.prefix}:{nonce}",
            "User-Agent": APP_SIGNATURE_HEADER,
            "Content-Type": "application/json",
          },
          json={
            "trackName": title,
            "artistName": artist,
            "albumName": album,
            "duration": duration,
            "plainLyrics": plain_lyrics,
            "syncedLyrics": synced_lyrics,
          },
          timeout=10,
        )
        self.emit("publish-done", response.status_code)
      except Exception as e:
        GLib.idle_add(self.emit, "publish-failed", e)
      finally:
        self._is_publish_running = False

    title = track.title
    artist = track.artist
    album = track.album
    duration = track.duration
    if not all([title, artist, album, duration, plain_lyrics, synced_lyrics]):
      raise AttributeError(
        "Any of required fields (title, artist, album, duration, plain_lyrics, synced_lyrics) wes treated as False"
      )
    if self._is_publish_running:
      raise PublishAlreadyRunning
    self._is_publish_running = True
    threading.Thread(
      target=do_publish,
      args=(title, artist, album, duration, plain_lyrics, synced_lyrics),
      daemon=True,
    ).start()

  async def fetch_lyrics_many(
    self,
    tracks: Iterable[BaseFile],
    on_progress: Callable,
    cancellable: threading.Event,
  ) -> dict[BaseFile, LRClibEntry]:
    """Asynchronously fetches lyrics for given iterable of files

    Parameters
    ----------
    tracks : Iterable[BaseFile]
      Iterable with madia files to parse lyrics for
    on_progress : Callable
      Callback for progress changes

    Returns
    -------
    dict[BaseFile, LRClibEntry]
      Conjunction for madia files and fetched lyrics. Will be `{BaseFile: None}` if no
      lyrics found
    """
    sem = asyncio.Semaphore(
      cast("int", Schema.get("root.settings.general.mass-downloading.parallel-amount"))
    )
    files_parse = len(cast("Sized", tracks))
    files_parsed = 0

    def emit_message(path: str, msg: str) -> None:
      GLib.idle_add(self.emit, "fetch-message", path, msg)

    def emit_state(path: str, state: FetchStates, data: object) -> None:
      GLib.idle_add(self.emit, "fetch-state", path, state, data)

    def fetch_failed(path: str, msg: str) -> None:
      emit_state(path, FetchStates.FAILED, None)
      emit_message(path, msg)

    async def sem_fetch(track: BaseFile) -> tuple[BaseFile, Optional[LRClibEntry]]:
      nonlocal files_parsed, on_progress, files_parse, cancellable

      if cancellable.is_set():
        raise asyncio.CancelledError

      async with sem:
        GLib.idle_add(self.emit, "fetch-started", track.path)
        logger.info("[FETCH] Starting fetching lyrics for %s", track.path)

        try:
          # First attempt using api_get
          response = await self.api_get(track)
          if not response.synced_lyrics:
            raise TrackNotFound  # Fallback to search to be able to use no album method  # noqa: TRY301
          files_parsed += 1
          emit_message(track.path, _("Fetched successfully"))
          emit_state(track.path, FetchStates.DONE, response)
          logger.info("[FETCH] Successfully fetched lyrics for %s", track.path)
          return track, response

        except TrackNotFound:
          # Second attempt using api_search
          emit_message(track.path, _("Fetch using /api/get failed, trying /api/search"))
          logger.warning(
            "[FETCH] Failed to fetch lyrics for %s using absolute /api/get", track.path
          )

          try:
            search_response = await self.api_search(
              unwrap(track.title), unwrap(track.artist), unwrap(track.album)
            )
            nearest = LRClibService.get_nearest(track, search_response)

            if nearest:
              if not nearest.synced_lyrics:
                with contextlib.suppress(SearchEmptyReturn):
                  logger.info("Trying to search %s with no album", track.path)
                  emit_message(track.path, _("Trying search with no album"))
                  search_response = await self.api_search(
                    unwrap(track.title), unwrap(track.artist)
                  )
                  nearest = LRClibService.get_nearest(track, search_response)
                  if nearest:
                    emit_message(track.path, _("Fetched successfully"))
                    emit_state(track.path, FetchStates.DONE, nearest)
                    logger.info(
                      "[FETCH] Successfully fetched lyrics for %s", track.path
                    )
                  else:
                    fetch_failed(track.path, _("No suitable lyrics found"))
                    logger.warning(
                      "[FETCH] No suitable lyrics found for %s using /api/search",
                      track.path,
                    )
                  files_parsed += 1
                  return track, nearest
              emit_message(track.path, _("Fetched successfully"))
              emit_state(track.path, FetchStates.DONE, nearest)
              logger.info("[FETCH] Successfully fetched lyrics for %s", track.path)
            else:
              files_parsed += 1
              fetch_failed(track.path, _("No suitable lyrics found"))
              logger.warning(
                "[FETCH] No suitable lyrics found for %s using /api/search", track.path
              )

            return track, nearest

          except SearchEmptyReturn:
            files_parsed += 1
            fetch_failed(track.path, _("No lyrics found"))
            logger.warning(
              "[FETCH] Failed to fetch lyrics for %s using /api/search", track.path
            )
            return track, None

        except Exception as e:
          emit_state(track.path, FetchStates.FAILED, e)

        finally:
          if cancellable.is_set():
            raise asyncio.CancelledError
          GLib.idle_add(on_progress, files_parsed / files_parse)

        return track, None

    tasks: list[asyncio.Task] = [sem_fetch(track) for track in tracks]  # ty:ignore[invalid-assignment]
    try:
      results = await asyncio.gather(*tasks)
    except asyncio.CancelledError:
      for t in tasks:
        t.cancel()
      await asyncio.gather(*tasks, return_exceptions=True)
      GLib.idle_add(on_progress, 1.0)
      raise
    GLib.idle_add(self.emit, "fetch-all-done")
    logger.info("[FETCH] All lyric fetches are done")
    return dict(results)

  @staticmethod
  def get_nearest(
    original: BaseFile, candidates: Iterable[LRClibEntry], weight: float = 0.2
  ) -> Optional[LRClibEntry]:
    """Gets the most suitable track for a given media file

    Parameters
    ----------
    original : BaseFile
      Original file against which the most suitable candidate is determined
    candidates : Iterable[LRClibEntry]
      Iterable of candidates against original comparable
    weight : float, optional
      Max deviation weight, by default 0.2. If candidate deviates from original on\
      this weight, it rejects

    Returns
    -------
    Optional[LRClibEntry]
      The most suitable candidate, or `None` if all of them devictes from that weight allows
    """

    def normalize(string: str) -> str:  # Remove double spaces
      return re.sub(r"\s+", " ", string.lower().strip())

    def string_similarity(a: str, b: str) -> float:
      return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

    def duration_similarity(d1: int, d2: int) -> float:
      if d1 == 0:
        return 0.0
      return max(0.0, 1 - abs(d1 - d2) / d1)

    def track_score(candidate: LRClibEntry) -> float:
      scores = [
        string_similarity(unwrap(original.title), candidate.track_name),
        string_similarity(unwrap(original.artist), candidate.artist_name),
        string_similarity(unwrap(original.album), candidate.album_name),
        duration_similarity(original.duration, candidate.duration),
      ]
      for score in scores:
        if score < 1 - weight:
          return 0.0

      base_score = sum(scores) / len(scores)
      if candidate.synced_lyrics:
        synced_lyrics_bonus = 1e-9
        return base_score + synced_lyrics_bonus

      return base_score

    best = None
    best_score = 0.0
    for candidate in candidates:
      score = track_score(candidate)
      if score > best_score:
        best_score = score
        best = candidate

    return best
