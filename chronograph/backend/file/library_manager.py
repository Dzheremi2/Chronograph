import asyncio
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Union
from uuid import uuid4

from chronograph.backend.db import db, set_db
from chronograph.backend.db.models import SchemaInfo, Track
from chronograph.backend.file_parsers import parse_file


class LibraryManager:
  current_library: Optional[Path] = None
  _SUPPORTED_SUFFIXES = (".ogg", ".flac", ".opus", ".mp3", ".wav", ".m4a", ".aac")

  @staticmethod
  def open_library(library: Union[str, Path]) -> bool:
    """Opens given Chronograph library

    Parameters
    ----------
    library : Union[str, Path]
      Path to a library

    Returns
    -------
    bool
      If library is valid (determined by `is_chr_library` file in it)
    """
    if (Path(library) / "is_chr_library").exists():
      lib_root = Path(library)
      db_path = lib_root / "library.db"

      set_db(str(db_path)).connect_and_create_tables()

      LibraryManager.current_library = lib_root
      return True
    return False

  @staticmethod
  def import_files(files: list[Path], move: bool = False) -> list[tuple[str, str]]:
    """Imports given files to library

    Parameters
    ----------
    files : list[Path]
      list of Paths to file intended for importing
    move : bool, optional
      If files should be imported by moving, not copying, by default False

    Returns
    -------
    list[tuple[str, str]]
      List of imported track UUIDs with their stored formats
    """
    imported: list[tuple[str, str]] = []
    lib_root = LibraryManager._require_library()

    content_dir = lib_root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    for src in files:
      result = LibraryManager._import_one(src, content_dir, move)
      if result:
        imported.append(result)
    return imported

  @staticmethod
  async def import_files_async(
    files: list[Path],
    move: bool = False,
    on_progress: Optional[Callable[[float], None]] = None,
    cancellable: Optional[threading.Event] = None,
  ) -> list[tuple[str, str]]:
    """Imports files in a background task with progress updates."""
    imported: list[tuple[str, str]] = []
    lib_root = LibraryManager._require_library()

    content_dir = lib_root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    total = max(len(files), 1)
    for index, src in enumerate(files, start=1):
      if cancellable and cancellable.is_set():
        break

      result = await asyncio.to_thread(
        LibraryManager._import_one, src, content_dir, move
      )
      if result:
        imported.append(result)
      if on_progress:
        on_progress(index / total)

    if on_progress:
      on_progress(1.0)
    return imported

  @staticmethod
  def _import_one(
    src: Path, content_dir: Path, move: bool
  ) -> Optional[tuple[str, str]]:
    tmp: Optional[Path] = None
    try:
      if not src.exists() or not src.is_file():
        return None

      fmt = src.suffix.lower()
      if fmt not in LibraryManager._SUPPORTED_SUFFIXES:
        return None

      if parse_file(src) is None:
        return None

      uuid = uuid4()
      dest = content_dir / f"{uuid}{fmt}"
      while dest.exists():
        uuid = uuid4()
        dest = content_dir / f"{uuid}{fmt}"

      tmp = content_dir / f".tmp_{uuid}"
      if move:
        src.rename(tmp)
      else:
        shutil.copy2(src, tmp)

      with db(atomic=True):
        Track.create(
          track_uuid=str(uuid),
          imported_at=int(time.time()),
          format=fmt,
          tags_json=[],
        )
      try:
        tmp.replace(dest)
      except Exception:
        with db(atomic=True):
          Track.delete_by_id(str(uuid))
        raise

      return (str(uuid), fmt)
    except Exception:
      try:
        if tmp and tmp.exists():
          tmp.unlink(missing_ok=True)
      except Exception as e:
        print(e)  # FIXME: REMOVE
    return None

  @staticmethod
  def delete_files(uuids: list[str]) -> int:
    """Delete given files by their UUIDs

    Parameters
    ----------
    uuids : list[str]
      list of UUIDs of files intended for deletion

    Returns
    -------
    int
      A numver of deleted files
    """
    deleted = 0
    lib_root = LibraryManager._require_library()
    content_dir = lib_root / "content"

    for uuid in uuids:
      try:
        track = Track.get_or_none(Track.track_uuid == uuid)
        track_format = track.format if track else ""
        with db(atomic=True):
          rows = Track.delete_by_id(uuid)

        file_path = LibraryManager.track_path(uuid, track_format)
        file_deleted = file_path.exists()
        file_path.unlink(missing_ok=True)

        if not file_deleted:
          for legacy_file in content_dir.glob(f"{uuid}.*"):
            legacy_file.unlink(missing_ok=True)
            file_deleted = True

        if rows or file_deleted:
          deleted += 1

      except Exception as e:
        print(e)  # FIXME: REMOVE

    return deleted

  @staticmethod
  def list_tracks() -> list[Track]:
    """Returns all tracks from the current library"""
    LibraryManager._require_library()
    with db():
      return list(Track.select().order_by(Track.imported_at))

  @staticmethod
  def track_path(track_uuid: str, track_format: Optional[str] = None) -> Path:
    """Builds a content path for the given track data"""
    lib_root = LibraryManager._require_library()
    content_dir = lib_root / "content"

    if track_format:
      suffix = track_format if track_format.startswith(".") else f".{track_format}"
      candidate = content_dir / f"{track_uuid}{suffix}"
      if candidate.exists():
        return candidate

    for candidate in content_dir.glob(f"{track_uuid}.*"):
      return candidate

    return content_dir / track_uuid

  @staticmethod
  def new_library(path: Path) -> Path:
    """Creates a new library at given Path

    Parameters
    ----------
    path : Path
      Path of a new library

    Returns
    -------
    Path
      Returns given path
    """
    base = "ChronographLibrary"
    i = 0

    while True:
      name = base if i == 0 else f"{base}_{i}"
      lib_root = path / name
      if not lib_root.exists():
        break
      i += 1

    lib_root.mkdir(parents=True)
    (lib_root / "content").mkdir()
    (lib_root / "is_chr_library").touch()

    db_path = lib_root / "library.db"
    set_db(str(db_path)).connect_and_create_tables()

    with db(atomic=True):
      SchemaInfo.insert(key="version", value="1").execute()

    return lib_root

  @staticmethod
  def _require_library() -> Path:
    if LibraryManager.current_library is None:
      raise RuntimeError("Library is not opened.")
    return LibraryManager.current_library
