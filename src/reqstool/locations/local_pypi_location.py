# Copyright © LFV

from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


class LocalPypiLocation(LocationInterface):
    path: str  # path to a local PyPI sdist tarball (.tar.gz)

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        return Utils.extract_targz(self.path, dst_path)
