# Copyright © LFV

import os
import zipfile

import pytest

from reqstool.locations.local_maven_location import LocalMavenLocation


def _make_zip(zip_path, top_level_dir, files):
    """Create a ZIP with the given top-level dir and {name: content} files."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in files.items():
            zf.writestr(f"{top_level_dir}/{name}", content)


def test_local_maven_location_extracts_zip(tmp_path):
    top_level = "ms-001-0.0.1-reqstool"
    zip_path = tmp_path / "artifact.zip"
    _make_zip(
        zip_path,
        top_level,
        {
            "requirements.yml": "metadata:\n  urn: ms-001\n",
            "reqstool_config.yml": "language: java\nbuild: maven\n",
        },
    )

    dst_path = tmp_path / "extracted"
    dst_path.mkdir()

    location = LocalMavenLocation(path=str(zip_path))
    result = location._make_available_on_localdisk(str(dst_path))

    assert result == str(dst_path / top_level)
    assert os.path.isfile(os.path.join(result, "requirements.yml"))
    assert os.path.isfile(os.path.join(result, "reqstool_config.yml"))


def test_local_maven_location_invalid_zip_raises(tmp_path):
    zip_path = tmp_path / "artifact.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dir-a/requirements.yml", "")
        zf.writestr("dir-b/requirements.yml", "")

    dst_path = tmp_path / "extracted"
    dst_path.mkdir()

    location = LocalMavenLocation(path=str(zip_path))
    with pytest.raises(ValueError, match="exactly one top-level directory"):
        location._make_available_on_localdisk(str(dst_path))


def test_local_maven_location_path():
    location = LocalMavenLocation(path="/tmp/artifact.zip")
    assert location.path == "/tmp/artifact.zip"
