# Copyright © LFV

from dataclasses import dataclass

from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


@dataclass
class LocalMavenLocation(LocationInterface):
    path: str  # path to a local Maven ZIP artifact (.zip)

    def _make_available_on_localdisk(self, dst_path: str):
        return Utils.extract_zip(self.path, dst_path)
