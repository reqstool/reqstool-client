# Copyright © LFV

import sys
import types

import pytest

from reqstool.locations import local_location

from reqstool.locations.local_location import LocalLocation
from reqstool_python_decorators.decorators.decorators import SVCs


@SVCs("SVC_SOURCE_0002")
def test_local_location(resource_funcname_rootdir_w_path):
    PATH = "/tmp/somepath"

    local_location = LocalLocation(path=PATH)

    assert local_location.path == PATH


def _make_dst(tmp_path):
    dst = tmp_path / "tmp" / "0" / "local_key"
    dst.mkdir(parents=True)
    return dst


def test_make_available_on_localdisk_links_project_directory(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "requirements.yml").write_text("hello")
    dst = _make_dst(tmp_path)

    result = LocalLocation(path=str(src))._make_available_on_localdisk(dst_path=dst)

    assert result == dst
    assert (dst / "requirements.yml").read_text() == "hello"


def test_make_available_on_localdisk_falls_back_to_junction_on_windows(tmp_path, monkeypatch):
    # Issue #457: symlinks need admin rights or Developer Mode on Windows
    src = tmp_path / "project"
    src.mkdir()
    dst = _make_dst(tmp_path)
    calls = []

    def no_symlink_privilege(*args, **kwargs):
        raise OSError(1314, "A required privilege is not held by the client")

    monkeypatch.setattr(local_location.os, "symlink", no_symlink_privilege)
    monkeypatch.setattr(local_location.sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "_winapi", types.SimpleNamespace(CreateJunction=lambda s, d: calls.append((s, d))))

    LocalLocation(path=str(src))._make_available_on_localdisk(dst_path=dst)

    assert calls == [(str(src), str(dst))]


def test_make_available_on_localdisk_reraises_symlink_error_off_windows(tmp_path, monkeypatch):
    src = tmp_path / "project"
    src.mkdir()
    dst = _make_dst(tmp_path)

    def no_symlink_privilege(*args, **kwargs):
        raise OSError(1, "Operation not permitted")

    monkeypatch.setattr(local_location.os, "symlink", no_symlink_privilege)
    monkeypatch.setattr(local_location.sys, "platform", "linux")

    with pytest.raises(OSError):
        LocalLocation(path=str(src))._make_available_on_localdisk(dst_path=dst)
