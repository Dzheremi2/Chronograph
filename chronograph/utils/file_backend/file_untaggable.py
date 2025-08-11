from .file import BaseFile


# pylint: disable=abstract-method
class FileUntaggable(BaseFile):
    __gtype_name__ = "FileUntaggable"

    def __init__(self, path: str):
        super().__init__(path)

        self.cover = None
