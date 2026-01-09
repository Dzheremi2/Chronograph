from typing import Optional, Union

from peewee import ConnectionContext, SqliteDatabase, _atomic

from chronograph.internal import Constants
from .models import Lyric, SchemaInfo, Track, TrackLyric, db_proxy

logger = Constants.DB_LOGGER

_db: Optional[SqliteDatabase] = None


def set_db(path: str):  # noqa: ANN201
  """Set DB to a given file

  Parameters
  ----------
  path : str
    Path to a DB file
  """
  global _db
  if _db is not None and not _db.is_closed():
    _db.close()

  _db = SqliteDatabase(path, pragmas={"foreign_keys": 1})
  db_proxy.initialize(_db)
  logger.debug("Database configured: %s", path)

  class Factory:
    def connect_and_create_tables(_self) -> None:  # noqa: N805
      """Connect to the database and ensure core tables exist."""
      if _db is None:
        raise RuntimeError("Database is not set. Call set_db(path) first.")

      _db.connect(reuse_if_open=True)
      _db.create_tables([Track, Lyric, TrackLyric, SchemaInfo])
      logger.debug("Database tables ensured: %s", _db.database)

  return Factory()


def db(atomic: bool = False) -> Union[ConnectionContext, _atomic]:
  """Use with `with` block to properly make transactions

  Parameters
  ----------
  atomic : bool, optional
    Should it use `db_proxy.atomic()` or not, by default False
  """
  return db_proxy.atomic() if atomic else db_proxy.connection_context()
