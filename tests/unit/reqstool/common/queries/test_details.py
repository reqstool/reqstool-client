# Copyright © LFV

import pytest

from reqstool.common.project_session import ProjectSession
from reqstool.common.queries.details import (
    get_mvr_details,
    get_requirement_details,
    get_requirement_status,
    get_svc_details,
)
from reqstool.locations.local_location import LocalLocation


@pytest.fixture
def session(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    s = ProjectSession(LocalLocation(path=path))
    s.build()
    yield s
    s.close()


def test_get_requirement_details_known(session):
    result = get_requirement_details("REQ_010", session.repo)
    assert result is not None
    assert result["type"] == "requirement"
    assert result["id"] == "REQ_010"
    assert "title" in result
    assert "significance" in result
    assert "description" in result
    assert "lifecycle" in result
    assert isinstance(result["references"], list)
    assert isinstance(result["implementations"], list)
    assert isinstance(result["svcs"], list)
    assert "location" in result
    assert result["source_paths"] == {}  # no urn_source_paths passed


def test_get_requirement_details_with_source_paths(session):
    result = get_requirement_details("REQ_010", session.repo, session.urn_source_paths)
    assert result is not None
    assert isinstance(result["source_paths"], dict)


def test_get_requirement_details_unknown(session):
    assert get_requirement_details("REQ_NONEXISTENT", session.repo) is None


def test_get_requirement_details_implementations(session):
    result = get_requirement_details("REQ_010", session.repo, session.urn_source_paths)
    assert result is not None
    assert len(result["implementations"]) > 0
    impl = result["implementations"][0]
    assert "element_kind" in impl
    assert "fqn" in impl


def test_get_svc_details_known(session):
    repo = session.repo
    svc_ids = [uid.id for uid in repo.get_all_svcs()]
    assert svc_ids
    result = get_svc_details(svc_ids[0], repo)
    assert result is not None
    assert result["type"] == "svc"
    assert "title" in result
    assert "verification" in result
    assert "requirement_ids" in result
    assert "test_summary" in result
    assert set(result["test_summary"].keys()) == {"passed", "failed", "skipped", "missing"}
    assert "mvrs" in result


def test_get_svc_details_unknown(session):
    assert get_svc_details("SVC_NONEXISTENT", session.repo) is None


def test_get_svc_details_requirement_ids_enriched(session):
    repo = session.repo
    svc_ids = [uid.id for uid in repo.get_all_svcs()]
    for svc_id in svc_ids:
        result = get_svc_details(svc_id, repo)
        assert result is not None
        for req_entry in result["requirement_ids"]:
            assert "id" in req_entry
            assert "urn" in req_entry
            assert "title" in req_entry
            assert "lifecycle_state" in req_entry
        break


def test_get_mvr_details_unknown(session):
    assert get_mvr_details("MVR_NONEXISTENT", session.repo) is None


def test_get_requirement_status_known(session):
    result = get_requirement_status("REQ_010", session.repo)
    assert result is not None
    assert result["id"] == "REQ_010"
    assert "lifecycle_state" in result
    assert "implementation" in result
    assert "test_summary" in result
    assert set(result["test_summary"].keys()) == {"passed", "failed", "skipped", "missing"}
    assert "meets_requirements" in result
    assert isinstance(result["meets_requirements"], bool)


def test_get_requirement_status_unknown(session):
    assert get_requirement_status("REQ_NONEXISTENT", session.repo) is None
