# Copyright © LFV

import os
import sys

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.locations.location import LocationInterface, make_safe_tmpdir_suffix


@Requirements("SOURCE_0002")
class LocalLocation(LocationInterface):
    path: str

    def tmpdir_key(self) -> str:
        return make_safe_tmpdir_suffix("local", f"file://{os.path.abspath(self.path)}")

    def _make_available_on_localdisk(self, dst_path: str):
        # dst_directory already exists but should be a symlink, remove
        os.rmdir(dst_path)

        src_path = os.path.abspath(self.path)

        try:
            os.symlink(src_path, dst_path, target_is_directory=True)
        except OSError:
            # Creating a symlink on Windows requires admin rights or Developer Mode.
            # A directory junction needs neither and behaves the same for local directories.
            if sys.platform != "win32":
                raise
            import _winapi

            _winapi.CreateJunction(src_path, str(dst_path))

        return dst_path
