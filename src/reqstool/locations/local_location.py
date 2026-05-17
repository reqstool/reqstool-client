# Copyright © LFV

import os

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.locations.location import LocationInterface, make_safe_tmpdir_suffix


@Requirements("REQ_001")
class LocalLocation(LocationInterface):
    path: str

    def tmpdir_key(self) -> str:
        return make_safe_tmpdir_suffix("local", f"file://{os.path.abspath(self.path)}")

    def _make_available_on_localdisk(self, dst_path: str):
        # dst_directory already exists but should a symlimk, remove
        os.rmdir(dst_path)

        src_path = os.path.abspath(self.path)

        dst_path_parent_directory, dst_path_last_segment = os.path.split(dst_path)

        dst_dir_fd = os.open(dst_path_parent_directory, os.O_RDONLY)

        symlink_name = str(dst_path_last_segment)  # Name of the symlink to be created
        os.symlink(src_path, symlink_name, dir_fd=dst_dir_fd, target_is_directory=True)

        os.close(dst_dir_fd)

        return dst_path
