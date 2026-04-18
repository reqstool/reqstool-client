# Copyright © LFV

from reqstool.common.project_session import ProjectSession
from reqstool.locations.local_location import LocalLocation


def test_build_standard_ms001(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    session = ProjectSession(LocalLocation(path=path))
    try:
        session.build()
        assert session.ready
        assert session.error is None
        assert session.repo is not None
        assert session.repo.get_initial_urn() == "ms-001"
        assert len(session.urn_source_paths) > 0
    finally:
        session.close()


def test_build_basic_ms101(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")
    session = ProjectSession(LocalLocation(path=path))
    try:
        session.build()
        assert session.ready
        assert session.error is None
        assert session.repo is not None
    finally:
        session.close()


def test_build_nonexistent_path():
    session = ProjectSession(LocalLocation(path="/nonexistent/path"))
    session.build()
    assert not session.ready
    assert session.error is not None
    assert session.repo is None


def test_rebuild(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    session = ProjectSession(LocalLocation(path=path))
    try:
        session.build()
        assert session.ready
        session.rebuild()
        assert session.ready
        assert session.repo is not None
    finally:
        session.close()


def test_close_idempotent(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    session = ProjectSession(LocalLocation(path=path))
    session.build()
    session.close()
    assert not session.ready
    assert session.repo is None
    session.close()  # should not raise


def test_urn_source_paths_populated(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    session = ProjectSession(LocalLocation(path=path))
    try:
        session.build()
        assert session.ready
        paths = session.urn_source_paths
        assert isinstance(paths, dict)
        assert len(paths) > 0
        for urn, file_map in paths.items():
            assert isinstance(urn, str)
            assert isinstance(file_map, dict)
    finally:
        session.close()


def test_urn_source_paths_cleared_on_close(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    session = ProjectSession(LocalLocation(path=path))
    session.build()
    assert len(session.urn_source_paths) > 0
    session.close()
    assert session.urn_source_paths == {}
