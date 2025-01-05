from typing import Union
from .file import BaseFile

class FileID3(BaseFile):
    """A ID3 compatible file class. Inherited from `BaseFile`

    Parameters
    --------
    path : str
        A path to file for loading
    """

    def load_cover(self) -> None: ...
    def load_str_data(self) -> None: ...
    def set_cover(self, img_path: Union[str, None]) -> None: ...
    def set_str_data(self, tag_name: str, new_val: str) -> None: ...
