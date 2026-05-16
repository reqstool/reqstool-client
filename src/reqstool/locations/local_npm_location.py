# Copyright © LFV

from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


class LocalNpmLocation(LocationInterface):
    path: str  # path to a local npm tarball (.tgz)

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        return Utils.extract_targz(self.path, dst_path)
