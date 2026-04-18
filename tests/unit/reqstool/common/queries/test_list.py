# Copyright © LFV

import pytest

from reqstool.common.project_session import ProjectSession
from reqstool.common.queries.list import get_list
from reqstool.locations.local_location import LocalLocation


@pytest.fixture
def repo(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    session = ProjectSession(LocalLocation(path=path))
    session.build()
    yield session.repo
    session.close()


def test_get_list_structure(repo):
    result = get_list(repo)
    assert isinstance(result, dict)
    assert "requirements" in result
    assert "svcs" in result
    assert "mvrs" in result


def test_get_list_requirements(repo):
    result = get_list(repo)
    reqs = result["requirements"]
    assert len(reqs) > 0
    for req in reqs:
        assert "id" in req
        assert "title" in req
        assert "lifecycle_state" in req
        assert isinstance(req["id"], str)
        assert isinstance(req["title"], str)


def test_get_list_svcs(repo):
    result = get_list(repo)
    svcs = result["svcs"]
    assert len(svcs) > 0
    for svc in svcs:
        assert "id" in svc
        assert "title" in svc
        assert "lifecycle_state" in svc
        assert "verification" in svc


def test_get_list_mvrs(repo):
    result = get_list(repo)
    # MVRs may be empty in this fixture — just check structure
    for mvr in result["mvrs"]:
        assert "id" in mvr
        assert "passed" in mvr
        assert isinstance(mvr["passed"], bool)
