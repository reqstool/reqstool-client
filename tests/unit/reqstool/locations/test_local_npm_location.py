# Copyright © LFV

import os
import tarfile

import pytest

from reqstool.locations.local_npm_location import LocalNpmLocation


def _make_tgz(tgz_path, top_level_dir, files):
    """Create a .tgz with the given top-level dir and {name: content} files."""
    with tarfile.open(tgz_path, "w:gz") as tf:
        for name, content in files.items():
            import io

            data = content.encode()
            info = tarfile.TarInfo(name=f"{top_level_dir}/{name}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_local_npm_location_extracts_tgz(tmp_path):
    top_level = "package"
    tgz_path = tmp_path / "artifact.tgz"
    _make_tgz(
        str(tgz_path),
        top_level,
        {
            "requirements.yml": "metadata:\n  urn: ts-001\n",
            "reqstool_config.yml": "language: typescript\nbuild: npm\n",
        },
    )

    dst_path = tmp_path / "extracted"
    dst_path.mkdir()

    location = LocalNpmLocation(path=str(tgz_path))
    result = location._make_available_on_localdisk(str(dst_path))

    assert result == str(dst_path / top_level)
    assert os.path.isfile(os.path.join(result, "requirements.yml"))
    assert os.path.isfile(os.path.join(result, "reqstool_config.yml"))


def test_local_npm_location_multiple_top_level_dirs_raises(tmp_path):
    tgz_path = tmp_path / "artifact.tgz"
    _make_tgz(str(tgz_path), "dir-a", {"requirements.yml": "", "extra/file.yml": ""})
    # Recreate with two top-level dirs
    import io

    with tarfile.open(str(tgz_path), "w:gz") as tf:
        for name in ("dir-a/requirements.yml", "dir-b/requirements.yml"):
            info = tarfile.TarInfo(name=name)
            info.size = 0
            tf.addfile(info, io.BytesIO(b""))

    dst_path = tmp_path / "extracted"
    dst_path.mkdir()

    location = LocalNpmLocation(path=str(tgz_path))
    with pytest.raises(ValueError, match="exactly one top-level directory"):
        location._make_available_on_localdisk(str(dst_path))


def test_local_npm_location_nonexistent_path_raises(tmp_path):
    location = LocalNpmLocation(path="/nonexistent/pkg.tgz")
    with pytest.raises(FileNotFoundError):
        location._make_available_on_localdisk(str(tmp_path))


def test_local_npm_location_path():
    location = LocalNpmLocation(path="/tmp/artifact.tgz")
    assert location.path == "/tmp/artifact.tgz"
