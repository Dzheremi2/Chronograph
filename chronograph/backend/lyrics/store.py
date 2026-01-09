import time
from typing import Optional
from uuid import uuid4

from chronograph.backend.db import db
from chronograph.backend.db.models import Lyric, TrackLyric
from chronograph.backend.lyrics.formats import ElrcLyrics, LrcLyrics, PlainLyrics


def _get_track_lyric(track_uuid: str, fmt: str) -> Optional[Lyric]:
  return (
    Lyric.select()
    .join(TrackLyric)
    .where((TrackLyric.track == track_uuid) & (Lyric.format == fmt))
    .get_or_none()
  )


def get_track_lyrics(track_uuid: str) -> dict[str, Lyric]:
  """Return all lyrics for a track keyed by format.

  Parameters
  ----------
  track_uuid : str
    Track UUID.

  Returns
  -------
  dict[str, Lyric]
    Mapping from format to Lyric model.
  """
  with db():
    query = Lyric.select().join(TrackLyric).where(TrackLyric.track == track_uuid)
    return {lyric.format: lyric for lyric in query}


def get_track_lyric(track_uuid: str, fmt: str) -> Optional[Lyric]:
  """Return a single lyric for a track by format.

  Parameters
  ----------
  track_uuid : str
    Track UUID.
  fmt : str
    Lyric format identifier.

  Returns
  -------
  Optional[Lyric]
    Lyric model or None when missing.
  """
  with db():
    return _get_track_lyric(track_uuid, fmt)


def _build_lyrics(fmt: str, content: str):
  fmt = fmt.lower()
  if fmt == "plain":
    return PlainLyrics(content)
  if fmt == "lrc":
    return LrcLyrics(content)
  if fmt == "elrc":
    return ElrcLyrics(content)
  return None


def save_track_lyric(track_uuid: str, fmt: str, content: str) -> Optional[Lyric]:
  """Create or update a lyric entry for a track.

  Parameters
  ----------
  track_uuid : str
    Track UUID.
  fmt : str
    Lyric format identifier.
  content : str
    Lyric text content.

  Returns
  -------
  Optional[Lyric]
    Saved lyric model, or None if content is empty.
  """
  content = content.strip()
  if not content:
    delete_track_lyric(track_uuid, fmt)
    return None

  lyrics_obj = _build_lyrics(fmt, content)
  finished = lyrics_obj.is_finished() if lyrics_obj else False

  now = int(time.time())
  with db(atomic=True):
    lyric = _get_track_lyric(track_uuid, fmt)
    if lyric is None:
      lyric = Lyric.create(
        lyrics_uuid=str(uuid4()),
        format=fmt,
        content=content,
        finished=finished,
        created_at=now,
        updated_at=now,
      )
      TrackLyric.create(track=track_uuid, lyric=lyric.lyrics_uuid)
    else:
      lyric.content = content
      lyric.finished = finished
      lyric.updated_at = now
      lyric.save()
  return lyric


def delete_track_lyric(track_uuid: str, fmt: str) -> None:
  """Delete a lyric entry for a track by format.

  Parameters
  ----------
  track_uuid : str
    Track UUID.
  fmt : str
    Lyric format identifier.
  """
  with db(atomic=True):
    lyric = _get_track_lyric(track_uuid, fmt)
    if lyric is None:
      return
    TrackLyric.delete().where(
      (TrackLyric.track == track_uuid) & (TrackLyric.lyric == lyric.lyrics_uuid)
    ).execute()
    Lyric.delete_by_id(lyric.lyrics_uuid)
