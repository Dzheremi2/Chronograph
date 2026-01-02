import contextlib
from typing import Optional

from peewee import ConnectionContext, SqliteDatabase

from .models import Lyric, SchemaInfo, Track, TrackLyric, db_proxy

_db: Optional[SqliteDatabase] = None


def set_db(path: str) -> None:  # noqa: D103
  global _db
  if _db is not None:
    with contextlib.suppress(Exception):
      _db.close()

  _db = SqliteDatabase(path, pragmas={"foreign_keys": 1})
  db_proxy.initialize(_db)


def connect_and_create_tables() -> None:  # noqa: D103
  if _db is None:
    raise RuntimeError("Database is not set. Call set_db(path) first.")

  _db.connect(reuse_if_open=True)
  _db.create_tables([Track, Lyric, TrackLyric, SchemaInfo])


def db() -> ConnectionContext:  # noqa: D103
  return db_proxy.connection_context()
