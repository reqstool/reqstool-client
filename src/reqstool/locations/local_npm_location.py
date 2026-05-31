# Copyright © LFV

import os

from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface, make_safe_tmpdir_suffix


class LocalNpmLocation(LocationInterface):
    path: str  # path to a local npm tarball (.tgz)

    def tmpdir_key(self) -> str:
        return make_safe_tmpdir_suffix("local_npm", f"file://{os.path.abspath(self.path)}")

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        return Utils.extract_targz(self.path, dst_path)
