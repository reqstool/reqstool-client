# Copyright © LFV

import os

from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface, make_safe_tmpdir_suffix


class LocalMavenLocation(LocationInterface):
    path: str  # path to a local Maven ZIP artifact (.zip)

    def tmpdir_key(self) -> str:
        return make_safe_tmpdir_suffix("local_maven", f"file://{os.path.abspath(self.path)}")

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        return Utils.extract_zip(self.path, dst_path)
