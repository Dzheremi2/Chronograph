from pathlib import Path
from typing import Union

from gi.repository import GObject

from chronograph.internal import Constants, Schema
from chronograph.utils.file_backend.file_manager import FileManager
from chronograph.utils.file_backend.song_card_model import SongCardModel
from chronograph.utils.file_parsers import parse_dir, parse_files
from chronograph.utils.lyrics import LyricsFile
from chronograph.utils.media import FileID3, FileMP4, FileUntaggable, FileVorbis
from chronograph.utils.miscellaneous import get_common_directory
from dgutils import GSingleton

logger = Constants.LOGGER


class LibraryModel(GObject.Object, metaclass=GSingleton):
  __gtype_name__ = "ChronographLibrary"

  def __init__(self) -> None:
    super().__init__()
    self.library = Constants.WIN.library
    self.library_list = Constants.WIN.library_list
    FileManager().connect("target-root-changed", self._on_target_root_changed)
    FileManager().connect("created", self._on_file_created)
    FileManager().connect("directory-removed", self._on_directory_removed)

  def open_dir(self, path: str) -> None:
    """Open a directory and load its files, updating window state

    Parameters
    ----------
    path : str
      Path of the directory to open
    """
    FileManager().set_directory(Path(path))

  def open_files(self, paths: list[str]) -> None:
    """Open multiple files, adding them to the library

    Parameters
    ----------
    paths : list[str]
      List of file paths to open
    """
    logger.info("Opening files:\n%s", "\n".join(paths))
    mutagen_files = parse_files(paths)
    if Constants.WIN.state.value != 3:
      self._clean_library()
    if self._load_files(mutagen_files):
      Constants.WIN.state = 3
    else:
      Constants.WIN.state = 0
    FileManager()
    Schema.set("root.state.library.session", "None")

  def reset_library(self) -> None:
    """Reset library to initial state"""
    logger.info("Resetting library to initial state")
    FileManager().set_directory(None)
    self._clean_library()
    Constants.WIN.state = 0

  def _clean_library(self) -> None:
    logger.info("Removing all cards from library")
    self.library.remove_all()
    self.library_list.remove_all()

  def _on_target_root_changed(self, _file_manager, new_path: str) -> None:
    logger.info("Opening '%s' directory", new_path)

    files = parse_dir(new_path)
    mutagen_files = parse_files(files)

    self._clean_library()
    Schema.set("root.state.library.session", new_path)

    if mutagen_files:
      self._load_files(mutagen_files)
      Constants.WIN.state = 2
    else:
      Constants.WIN.state = 1

  def _load_files(
    self, mutagen_files: tuple[Union[FileID3, FileMP4, FileVorbis, FileUntaggable]]
  ) -> bool:
    def songcard_idle(
      file: Union[FileID3, FileVorbis, FileMP4, FileUntaggable],
    ) -> None:
      model = SongCardModel(file, LyricsFile(Path(file.path)))
      song_card = model.widget
      self.library.append(song_card)
      self.library_list.append(song_card.get_list_mode())
      song_card.get_parent().set_focusable(False)
      logger.debug(
        "SongCard for song '%s -- %s' was added",
        model.title_display,
        model.artist_display,
      )

    if not mutagen_files:
      return False
    for mutagen_file in mutagen_files:
      if isinstance(mutagen_file, (FileID3, FileVorbis, FileMP4, FileUntaggable)):
        GObject.idle_add(songcard_idle, mutagen_file)
    Constants.WIN.open_source_button.set_icon_name("open-source-symbolic")
    if path := get_common_directory([f.path for f in mutagen_files]):
      Schema.set("root.state.library.session", path)
    return True

  def _on_file_created(self, _file_manager, created_file: str) -> None:
    self._load_files(parse_files((created_file,)))

  def _on_directory_removed(self, _file_manager, removed_dir: str) -> None:
    removed_path = Path(removed_dir)
    children_to_remove = []

    for child in self.library:
      model = child.get_child().model
      if model and Path(model.mfile.path).is_relative_to(removed_path):
        children_to_remove.append(child)
    for child in children_to_remove:
      self.library.remove(child)
      self.library_list.remove(child.get_child().get_list_mode())
