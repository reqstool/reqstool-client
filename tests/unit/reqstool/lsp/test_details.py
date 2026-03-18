# Copyright © LFV

import pytest

from reqstool.lsp.features.details import get_mvr_details, get_requirement_details, get_svc_details
from reqstool.lsp.project_state import ProjectState


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_get_requirement_details_known(project):
    result = get_requirement_details("REQ_010", project)
    assert result is not None
    assert result["type"] == "requirement"
    assert result["id"] == "REQ_010"
    assert "title" in result
    assert "significance" in result
    assert "description" in result
    assert "lifecycle" in result
    assert "references" in result
    assert isinstance(result["references"], list)
    assert "implementations" in result
    assert isinstance(result["implementations"], list)
    assert "svcs" in result
    assert isinstance(result["svcs"], list)


def test_get_requirement_details_unknown(project):
    result = get_requirement_details("REQ_NONEXISTENT", project)
    assert result is None


def test_get_svc_details_known(project):
    svc_ids = project.get_all_svc_ids()
    assert svc_ids, "No SVCs in test fixture"
    result = get_svc_details(svc_ids[0], project)
    assert result is not None
    assert result["type"] == "svc"
    assert result["id"] == svc_ids[0]
    assert "title" in result
    assert "verification" in result
    assert "lifecycle" in result
    assert "requirement_ids" in result
    assert "test_annotations" in result
    assert isinstance(result["test_annotations"], list)
    assert "test_results" in result
    assert isinstance(result["test_results"], list)
    assert "mvrs" in result


def test_get_svc_details_unknown(project):
    result = get_svc_details("SVC_NONEXISTENT", project)
    assert result is None


def test_get_mvr_details_unknown(project):
    # No MVRs in the test_standard fixture; get_mvr should return None
    result = get_mvr_details("MVR_NONEXISTENT", project)
    assert result is None


def test_get_requirement_details_fields(project):
    result = get_requirement_details("REQ_010", project)
    assert result is not None
    assert result["urn"].endswith(":REQ_010")
    assert result["lifecycle"]["state"] in ("draft", "effective", "deprecated", "obsolete")
    assert isinstance(result["categories"], list)


def test_get_requirement_details_implementations(project):
    # annotations.yml has implementations for REQ_010
    result = get_requirement_details("REQ_010", project)
    assert result is not None
    assert len(result["implementations"]) > 0
    impl = result["implementations"][0]
    assert "element_kind" in impl
    assert "fqn" in impl
    assert impl["element_kind"] in ("CLASS", "METHOD", "FIELD", "ENUM", "INTERFACE", "RECORD")


def test_get_svc_details_test_results(project):
    # Find a SVC that has test annotations (SVCs in the fixture are linked to test methods)
    svc_ids = project.get_all_svc_ids()
    # Look for an SVC that has test_annotations in the fixture
    for svc_id in svc_ids:
        result = get_svc_details(svc_id, project)
        assert result is not None
        if result["test_annotations"]:
            assert all("element_kind" in a and "fqn" in a for a in result["test_annotations"])
            assert all("fqn" in t and "status" in t for t in result["test_results"])
            assert all(t["status"] in ("passed", "failed", "skipped", "missing") for t in result["test_results"])
            break
