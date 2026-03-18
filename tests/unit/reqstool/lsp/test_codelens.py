# Copyright © LFV

import pytest

from reqstool.lsp.features.codelens import handle_code_lens
from reqstool.lsp.project_state import ProjectState

URI = "file:///test.py"


def test_codelens_no_project():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_code_lens(URI, text, "python", None)
    assert result == []


def test_codelens_project_not_ready():
    state = ProjectState(reqstool_path="/nonexistent")
    result = handle_code_lens(URI, '@Requirements("REQ_010")', "python", state)
    assert result == []


def test_codelens_no_annotations():
    result = handle_code_lens(URI, "def foo(): pass", "python", None)
    assert result == []


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_codelens_requirement_annotation(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_code_lens(URI, text, "python", project)
    assert len(result) == 1
    lens = result[0]
    assert lens.command is not None
    assert "REQ_010" in lens.command.title
    assert lens.command.command == "reqstool.openDetails"
    assert lens.command.arguments[0]["type"] == "requirement"


def test_codelens_svc_annotation(project):
    svc_ids = project.get_all_svc_ids()
    assert svc_ids
    text = f'@SVCs("{svc_ids[0]}")\ndef test_foo(): pass'
    result = handle_code_lens(URI, text, "python", project)
    assert len(result) == 1
    lens = result[0]
    assert svc_ids[0] in lens.command.title
    assert lens.command.arguments[0]["type"] == "svc"


def test_codelens_multiple_ids_same_line(project):
    req_ids = project.get_all_requirement_ids()
    assert len(req_ids) >= 2
    text = f'@Requirements("{req_ids[0]}", "{req_ids[1]}")\ndef foo(): pass'
    result = handle_code_lens(URI, text, "python", project)
    # Both IDs on same line → one lens
    assert len(result) == 1
    assert req_ids[0] in result[0].command.title
    assert req_ids[1] in result[0].command.title
