import contextlib
from typing import Optional, Union

from peewee import ConnectionContext, SqliteDatabase, _atomic

from .models import Lyric, SchemaInfo, Track, TrackLyric, db_proxy

_db: Optional[SqliteDatabase] = None


def set_db(path: str):  # noqa: ANN201, D103
  global _db
  if _db is not None and not _db.is_closed():
    _db.close()

  _db = SqliteDatabase(path, pragmas={"foreign_keys": 1})
  db_proxy.initialize(_db)

  class Factory:
    def connect_and_create_tables(_self) -> None:  # noqa: N805
      if _db is None:
        raise RuntimeError("Database is not set. Call set_db(path) first.")

      _db.connect(reuse_if_open=True)
      _db.create_tables([Track, Lyric, TrackLyric, SchemaInfo])

  return Factory()


def db(atomic: bool = False) -> Union[ConnectionContext, _atomic]:  # noqa: D103
  return db_proxy.atomic() if atomic else db_proxy.connection_context()
