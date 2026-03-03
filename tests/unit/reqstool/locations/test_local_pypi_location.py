# Copyright © LFV

import io
import os
import tarfile

import pytest

from reqstool.locations.local_pypi_location import LocalPypiLocation


def _make_targz(targz_path, top_level_dir, files):
    """Create a tar.gz with the given top-level dir and {name: content} files."""
    with tarfile.open(targz_path, "w:gz") as tf:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=f"{top_level_dir}/{name}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_local_pypi_location_extracts_targz(tmp_path):
    top_level = "mypackage-0.0.1"
    targz_path = tmp_path / "package.tar.gz"
    _make_targz(
        str(targz_path),
        top_level,
        {
            "reqstool_config.yml": "language: python\nbuild: hatch\n",
            "docs/reqstool/requirements.yml": "metadata:\n  urn: mypackage\n",
        },
    )

    dst_path = tmp_path / "extracted"
    dst_path.mkdir()

    location = LocalPypiLocation(path=str(targz_path))
    result = location._make_available_on_localdisk(str(dst_path))

    assert result == str(dst_path / top_level)
    assert os.path.isfile(os.path.join(result, "reqstool_config.yml"))
    assert os.path.isfile(os.path.join(result, "docs", "reqstool", "requirements.yml"))


def test_local_pypi_location_invalid_targz_raises(tmp_path):
    targz_path = tmp_path / "package.tar.gz"
    with tarfile.open(str(targz_path), "w:gz") as tf:
        for top in ("dir-a", "dir-b"):
            data = b""
            info = tarfile.TarInfo(name=f"{top}/reqstool_config.yml")
            info.size = 0
            tf.addfile(info, io.BytesIO(data))

    dst_path = tmp_path / "extracted"
    dst_path.mkdir()

    location = LocalPypiLocation(path=str(targz_path))
    with pytest.raises(ValueError, match="exactly one top-level directory"):
        location._make_available_on_localdisk(str(dst_path))


def test_local_pypi_location_path():
    location = LocalPypiLocation(path="/tmp/package.tar.gz")
    assert location.path == "/tmp/package.tar.gz"
