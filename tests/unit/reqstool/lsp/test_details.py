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
