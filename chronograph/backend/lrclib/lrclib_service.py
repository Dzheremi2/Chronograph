import asyncio
import re
import threading
from difflib import SequenceMatcher
from typing import Coroutine, Iterable, Optional, Union

import httpx

from chronograph.backend.lrclib.lrclib_enums import ReqResultCode
from chronograph.backend.media.file import BaseFile
from chronograph.internal import Constants
from dgutils import Singleton

from .responses import LRClibChallenge, LRClibEntry, LRClibResponse

logger = Constants.LRCLIB_LOGGER


class LRClibService(metaclass=Singleton):
  __gtype_name__ = "LRClibService"

  _APP_SIGNATURE_HEADER: str = (
    f"Chronograph v{Constants.VERSION} (https://github.com/Dzheremi2/Chronograph)"
  )

  def __init__(self) -> None:
    super().__init__()

    self._loop = asyncio.get_event_loop()

  async def _api_get(
    self, track_name: str, artist_name: str, album_name: str, duration: int
  ) -> LRClibResponse:
    async with httpx.AsyncClient() as client:
      try:
        params = {
          "track_name": track_name,
          "artist_name": artist_name,
          "album_name": album_name,
          "duration": duration,
        }
        resp = await client.get(
          "https://lrclib.net/api/get",
          params=params,
          headers={"User-Agent": self._APP_SIGNATURE_HEADER},
        )
        if resp.status_code != 404:
          resp_json = resp.json()
          return LRClibResponse(
            [
              LRClibEntry(
                resp_json["id"],
                resp_json["trackName"],
                resp_json["artistName"],
                resp_json["albumName"],
                resp_json["duration"],
                resp_json["instrumental"],
                resp_json["plainLyrics"],
                resp_json["syncedLyrics"],
              )
            ]
          )
        return LRClibResponse(
          code=resp.status_code, name=resp_json["name"], message=resp_json["message"]
        )
      except Exception as e:
        return LRClibResponse(code=-1, message=str(e))

  def api_get(
    self, track_name: str, artist_name: str, album_name: str, duration: int
  ) -> None:
    """Starts an async operation for LRClib `/api/get` endpoint

    Parameters
    ----------
    track_name : str
        Title of the track
    artist_name : str
        Artist of the track
    album_name : str
        Album of the track
    duration : int
        Duration of the track
    """
    return LRClibService.run_sync(
      self._api_get(track_name, artist_name, album_name, duration)
    )

  async def _api_search(
    self, track_name: str, artist_name: Optional[str], album_name: Optional[str]
  ) -> LRClibResponse:
    async with httpx.AsyncClient() as client:
      try:
        params = {
          "track_name": track_name.strip(),
          "artist_name": artist_name.strip(),
          "album_name": album_name.strip(),
        }
        resp = await client.get(
          "https://lrclib.net/api/search",
          params=params,
          headers={"User-Agent": self._APP_SIGNATURE_HEADER},
        )
        if resp.json():
          resp_json = resp.json()
          tracks = []
          for item in resp_json:
            track = LRClibEntry(
              item["id"],
              item["trackName"],
              item["artistName"],
              item["albumName"],
              item["duration"],
              item["instrumental"],
              item["plainLyrics"],
              item["syncedLyrics"],
            )
            tracks.append(track)
          return LRClibResponse(tracks, resp.status_code)
        resp_json = resp.json()
        return LRClibResponse(
          code=ReqResultCode.NOT_FOUND.value,
          name="SearchEmptyResult",
          message="No tracks found for this request",
        )
      except Exception as e:
        return LRClibResponse(code=-1, message=str(e))

  def api_search(
    self,
    track_name: str,
    artist_name: str = "",
    album_name: str = "",
  ) -> LRClibResponse:
    """Starts an async operation for LRClib `/api/search` endpoint

    Parameters
    ----------
    track_name : str
        Title of the track
    artist_name : str, optional
        Artst of the track, by default ""
    album_name : str, optional
        Album of the track, by default ""

    Returns
    -------
    LRClibResponse
        Response with either valid tracks, or with error description
    """
    return LRClibService.run_sync(self._api_search(track_name, artist_name, album_name))

  async def _api_request_challenge(self) -> Union[LRClibChallenge, LRClibResponse]:
    async with httpx.AsyncClient() as client:
      try:
        resp = await client.post(
          "https://lrclib.net/api/request-challenge",
          headers={"User-Agent": self._APP_SIGNATURE_HEADER},
        )
        resp_json = resp.json()
        return LRClibChallenge(resp_json["prefix"], resp_json["target"])
      except Exception:
        return LRClibResponse(code=resp.status_code)

  def api_request_challenge(self) -> Union[LRClibChallenge, LRClibResponse]:
    """Starts and async operation for LRClib `/api/request-challenge` endpoint

    Returns
    -------
    Union[LRClibChallenge, LRClibResponse]
        Either valid prefix and target in dataclass, or LRClibResponse with error code
    """
    return LRClibService.run_sync(self._api_request_challenge)

  async def _api_publish(
    self,
    track_name: str,
    artist_name: str,
    album_name: str,
    duration: int,
    plain_lyrics: str,
    synced_lyrics: str,
  ) -> LRClibResponse:
    async with httpx.AsyncClient() as client:
      try:
        params = {
          "trackName": track_name,
          "artistName": artist_name,
          "albumName": album_name,
          "duration": duration,
          "plainLyrics": plain_lyrics,
          "syncedLyrics": synced_lyrics,
        }
        resp = await client.post(
          "https://lrclib.net/api/publish",
          params=params,
          headers={"User-Agent": self._APP_SIGNATURE_HEADER, "X-Publish-Token": "1212"},
        )
        resp_json = resp.json()
        if resp.status_code == ReqResultCode.PUBLISH_SUCCESS.value:
          return LRClibResponse(code=resp.status_code)
        if resp.status_code == ReqResultCode.FAILURE.value:
          return LRClibResponse(
            code=resp.status_code, name=resp_json["name"], message=resp_json["message"]
          )
      except Exception:
        return LRClibResponse(code=resp.status_code)

  def api_publish(
    self,
    track_name: str,
    artist_name: str,
    album_name: str,
    duration: int,
    plain_lyrics: str,
    synced_lyrics: str,
  ) -> LRClibResponse:
    """Starts and async operation for LRClib `/api/publish` endpoint

    Parameters
    ----------
    track_name : str
        Title of the track
    artist_name : str
        Artist of the track
    album_name : str
        Album of the track
    duration : int
        Duration of the track
    plain_lyrics : str
        Plain lyrics of the track
    synced_lyrics : str
        Synced lyrics of the track

    Returns
    -------
    LRClibResponse
        Response about how request was
    """
    return LRClibService.run_sync(
      self._api_publish(
        track_name, artist_name, album_name, duration, plain_lyrics, synced_lyrics
      )
    )

  async def _fetch_lyrics_many(
    self, tracks: Iterable[BaseFile]
  ) -> dict[BaseFile, LRClibEntry]:
    sem = asyncio.Semaphore(5)

    async def sem_fetch(track: BaseFile) -> tuple[BaseFile, Optional[LRClibEntry]]:
      async with sem:
        resp: LRClibResponse = await self._api_get(
          track.title, track.artist, track.album, track.duration
        )
        if resp.code != ReqResultCode.NOT_FOUND.value and resp.response:
          return track, resp.response[0]

        search_resp = await self._api_search(track.title, track.artist, track.album)
        if search_resp.code != ReqResultCode.NOT_FOUND.value and search_resp.response:
          nearest = LRClibService.get_nearest(track, search_resp.response)
          return track, nearest
        return track, None

    tasks = [sem_fetch(track) for track in tracks]
    results = await asyncio.gather(*tasks)
    return dict(results)

  def featch_lyrics_many(
    self, tracks: Iterable[BaseFile]
  ) -> dict[BaseFile, LRClibEntry]:
    """Starts an async operation of fetching lyrics for given tracks

    Parameters
    ----------
    tracks : Sequence[BaseFile]
        Any iterable with BaseFile subclasses (media files)

    Returns
    -------
    dict[BaseFile, LRClibEntry]
      Conjunction of the media file and founded tracks. Gather lyrics from `synced_lyrics` and `plain_lyrics` attributes
    """
    return LRClibService.run_sync(self._fetch_lyrics_many(tracks))

  @staticmethod
  def run_sync(coro: Coroutine):  # noqa: ANN205, D102
    try:
      return asyncio.run(coro)
    except RuntimeError:
      result = {}

      def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result["value"] = loop.run_until_complete(coro)
        loop.close()

      t = threading.Thread(target=runner)
      t.start()
      t.join()
      return result["value"]

  @staticmethod
  def get_nearest(
    original: BaseFile, candidates: Iterable[LRClibEntry], weight: int = 0.2
  ) -> Optional[LRClibEntry]:
    """Gets the most suitable track for a given media file

    Parameters
    ----------
    original : BaseFile
        Original file against which the most suitable candidate is determined
    candidates : Iterable[LRClibEntry]
        Iterable of candidates against original comparable
    weight : int, optional
        Max deviation weight, by default 0.2. If candidate deviates from original on\
        this weight, it rejects

    Returns
    -------
    Optional[LRClibEntry]
        The most suitable candidate, or `None` if all of them devictes from that weight allows
    """

    def normalize(string: str) -> str:
      return re.sub(r"\s+", " ", string.lower().strip())

    def string_similarity(a: str, b: str) -> float:
      return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

    def duration_similarity(d1: int, d2: int) -> float:
      if d1 == 0:
        return 0.0
      return max(0.0, 1 - abs(d1 - d2) / d1)

    def track_score(candidate: LRClibEntry) -> float:
      scores = [
        string_similarity(original.title, candidate.track_name),
        string_similarity(original.artist, candidate.artist_name),
        string_similarity(original.album, candidate.album_name),
        duration_similarity(original.duration, candidate.duration),
      ]
      for score in scores:
        if score < 1 - weight:
          return 0.0
      return sum(scores) / len(scores)

    best = None
    best_score = 0.0
    for candidate in candidates:
      score = track_score(candidate)
      if score > best_score:
        best_score = score
        best = candidate

    return best
