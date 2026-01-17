import contextlib
import time
from typing import Optional, Union
from uuid import uuid4

from chronograph.backend.db import db
from chronograph.backend.db.models import Lyric, TrackLyric
from chronograph.backend.lyrics.chronie import ChronieLyrics
from chronograph.backend.lyrics.formats import chronie_from_text, detect_lyric_format
from chronograph.backend.lyrics.interfaces import LyricFormat
from chronograph.internal import Constants

logger = Constants.DB_LOGGER


def _get_track_lyric_model(track_uuid: str) -> Optional[Lyric]:
  query = (
    Lyric.select()
    .join(TrackLyric)
    .where(TrackLyric.track == track_uuid)
    .order_by(Lyric.updated_at.desc(), Lyric.created_at.desc())
  )
  return query.first()


def get_track_lyric(track_uuid: str) -> Optional[ChronieLyrics]:
  """Return Chronie lyrics for a track."""
  with db():
    lyric = _get_track_lyric_model(track_uuid)
    if lyric is None:
      return None
    return _load_chronie(lyric.content)


def save_track_lyric(
  track_uuid: str, lyrics: Union[ChronieLyrics, LyricFormat, str]
) -> Optional[Lyric]:
  """Create or update Chronie lyrics for a track."""
  chronie = _coerce_chronie(lyrics)
  if chronie is None or not chronie:
    delete_track_lyric(track_uuid)
    return None

  content = chronie.to_json()
  finished = chronie.is_finished()
  now = int(time.time())

  with db(atomic=True):
    lyric = _get_track_lyric_model(track_uuid)
    if lyric is None:
      lyric = Lyric.create(
        lyrics_uuid=str(uuid4()),
        content=content,
        finished=finished,
        created_at=now,
        updated_at=now,
      )
      TrackLyric.create(track=track_uuid, lyric=lyric.lyrics_uuid)
      logger.debug("Lyric created: track=%s", track_uuid)
    else:
      lyric.content = content
      lyric.finished = finished
      lyric.updated_at = now
      lyric.save()
      logger.debug("Lyric updated: track=%s", track_uuid)
  return lyric


def delete_track_lyric(track_uuid: str) -> None:
  """Delete lyrics for a track."""
  with db(atomic=True):
    lyric_ids = [
      row.lyric
      for row in TrackLyric.select(TrackLyric.lyric).where(
        TrackLyric.track == track_uuid
      )
    ]
    if not lyric_ids:
      return
    TrackLyric.delete().where(TrackLyric.track == track_uuid).execute()
    Lyric.delete().where(Lyric.lyrics_uuid.in_(lyric_ids)).execute()
    logger.info("Lyrics deleted: track=%s", track_uuid)


def _coerce_chronie(
  lyrics: Union[ChronieLyrics, LyricFormat, str],
) -> Optional[ChronieLyrics]:
  if isinstance(lyrics, ChronieLyrics):
    return lyrics
  if isinstance(lyrics, LyricFormat):
    return lyrics.to_chronie()
  if isinstance(lyrics, str):
    return chronie_from_text(lyrics)
  return None


def _load_chronie(content: str) -> Optional[ChronieLyrics]:
  if not content or not content.strip():
    return None
  with contextlib.suppress(Exception):
    return ChronieLyrics.from_json(content)
  with contextlib.suppress(Exception):
    return ChronieLyrics.from_yaml(content)
  with contextlib.suppress(Exception):
    return detect_lyric_format(content).to_chronie()
  return None
