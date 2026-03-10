# Copyright © LFV

from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


class LocalMavenLocation(LocationInterface):
    path: str  # path to a local Maven ZIP artifact (.zip)

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        return Utils.extract_zip(self.path, dst_path)
