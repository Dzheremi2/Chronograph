import shutil
import time
from pathlib import Path
from typing import Optional, Union
from uuid import uuid4

from chronograph.backend.db import db, set_db
from chronograph.backend.db.models import SchemaInfo, Track


class LibraryManager:
  current_library: Optional[Path] = None

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
    if "is_chr_library" in tuple(Path(library).iterdir()):
      lib_root = Path(library)
      db_path = lib_root / "library.db"

      set_db(str(db_path)).connect_and_create_tables()

      LibraryManager.current_library = lib_root
      return True
    return False

  @staticmethod
  def import_files(files: list[Path], move: bool = False) -> int:
    """Imports given files to library

    Parameters
    ----------
    files : list[Path]
      list of Paths to file intended for importing
    move : bool, optional
      If files should be imported by moving, not copying, by default False

    Returns
    -------
    int
      A number of imported files
    """
    imported = 0
    lib_root = LibraryManager._require_library()

    content_dir = lib_root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    for src in files:
      try:
        uuid = uuid4()
        dest = content_dir / str(uuid)
        while dest.exists():
          uuid = uuid4()
          dest = content_dir / str(uuid)

        tmp = content_dir / f".tmp_{uuid}"
        if move:
          src.rename(tmp)
        else:
          shutil.copy2(src, tmp)

        with db(atomic=True):
          Track.create(
            track_uuid=str(uuid),
            imported_at=int(time.time()),
            tags_json=[],
          )
        try:
          tmp.replace(dest)
        except Exception:
          with db(atomic=True):
            Track.delete_by_id(str(uuid))
          raise

        imported += 1

      except Exception:
        try:
          if "tmp" in locals() and tmp.exists():
            tmp.unlink(missing_ok=True)
        except Exception as e:
          print(e)  # FIXME: REMOVE
    return imported

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
        with db(atomic=True):
          rows = Track.delete_by_id(uuid)

        file_deleted = (content_dir / uuid).exists()
        (content_dir / uuid).unlink(missing_ok=True)

        if rows or file_deleted:
          deleted += 1

      except Exception as e:
        print(e)  # FIXME: REMOVE

    return deleted

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
