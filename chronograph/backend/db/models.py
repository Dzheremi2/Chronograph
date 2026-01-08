from typing import Optional

from peewee import (
  BooleanField,
  CompositeKey,
  DatabaseProxy,
  ForeignKeyField,
  IntegerField,
  Model,
  TextField,
  fn,
)
from playhouse.sqlite_ext import JSONField

db_proxy = DatabaseProxy()


class ChronographDatabase(Model):
  class Meta:  # noqa: D106
    database = db_proxy


class Track(ChronographDatabase):
  """
  SQL::

    CREATE TABLE IF NOT EXISTS tracks (
      track_uuid   TEXT PRIMARY KEY,        -- Unique ID of the track
      imported_at  INTEGER NOT NULL,        -- Time, when track was imported
      format       TEXT NOT NULL,           -- Format of the media
      tags_json    JSON NOT NULL DEFAULT [] -- List of tags assigned to the track
    )
  """

  track_uuid = TextField(primary_key=True)
  imported_at = IntegerField()
  format = TextField()
  tags_json = JSONField(default=list)

  class Meta:  # noqa: D106
    table_name = "tracks"

  @property
  def latest_lyric_update(self) -> Optional[int]:
    query = (
      Lyric.select(fn.MAX(Lyric.updated_at))
      .join(TrackLyric)
      .where(TrackLyric.track == self)
    )
    return query.scalar()


class Lyric(ChronographDatabase):
  """
  SQL::

    CREATE TABLE IF NOT EXISTS lyrics (
      lyrics_uuid  TEXT PRIMARY KEY,               -- Unique ID of the lyric
      format       TEXT NOT NULL,                  -- Lyric format (LRC, eLRC, TTML, SRT, ...)
      content      TEXT NOT NULL DEFAULT '',       -- Lyric text
      finished     BOOLEAN NOT NULL DEFAULT FALSE, -- State of the lyric synchronization
      created_at   INTEGER NOT NULL,               -- Creation time
      updated_at   INTEGER                         -- Last modified time
    )
  """

  lyrics_uuid = TextField(primary_key=True)
  format = TextField()
  content = TextField(default="")
  finished = BooleanField(default=False)
  created_at = IntegerField()
  updated_at = IntegerField(null=True)

  class Meta:  # noqa: D106
    table_name = "lyrics"
    indexes = ((("format",), False),)


class TrackLyric(ChronographDatabase):
  """
  SQL::

    CREATE TABLE IF NOT EXISTS track_lyrics (
      track_uuid   TEXT NOT NULL,            -- Unique ID of the track
      lyrics_uuid  TEXT NOT NULL,            -- Unique ID of the lyric
      PRIMARY KEY (track_uuid, lyrics_uuid), -- Unique ID of the binding
      -- Automatically detele binding if track or lyric was deleted
      FOREIGN KEY (track_uuid) REFERENCES tracks(track_uuid) ON DELETE CASCADE,
      FOREIGN KEY (lyrics_uuid) REFERENCES lyrics(lyrics_uuid) ON DELETE CASCADE
    )
  """

  track = ForeignKeyField(
    Track,
    field=Track.track_uuid,
    backref="track_lyrics",
    on_delete="CASCADE",
    column_name="track_uuid",
  )
  lyric = ForeignKeyField(
    Lyric,
    field=Lyric.lyrics_uuid,
    backref="track_lyrics",
    on_delete="CASCADE",
    column_name="lyrics_uuid",
  )

  class Meta:  # noqa: D106
    table_name = "track_lyrics"
    primary_key = CompositeKey("track", "lyric")
    indexes = (
      (("track",), False),
      (("lyric",), False),
    )


class SchemaInfo(ChronographDatabase):
  """
  SQL::

    CREATE TABLE IF NOT EXISTS schema_info (
      key   TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )

  Current specs:

    version: int(repr as str) = "1"
    tags: JSON<str>(repr as str) = "[]"
  """

  key = TextField(primary_key=True)
  value = TextField()

  class Meta:  # noqa: D106
    table_name = "schema_info"
