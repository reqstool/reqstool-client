# Copyright © LFV

import pytest

from reqstool.lsp.features.workspace_symbols import handle_workspace_symbols
from reqstool.lsp.project_state import ProjectState


class _MockWorkspaceManager:
    def __init__(self, projects):
        self._projects = projects

    def all_projects(self):
        return self._projects


def test_workspace_symbols_empty_workspace():
    manager = _MockWorkspaceManager([])
    result = handle_workspace_symbols("", manager)
    assert result == []


def test_workspace_symbols_project_not_ready():
    state = ProjectState(reqstool_path="/nonexistent")
    manager = _MockWorkspaceManager([state])
    result = handle_workspace_symbols("", manager)
    assert result == []


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_workspace_symbols_empty_query_returns_all(project):
    manager = _MockWorkspaceManager([project])
    result = handle_workspace_symbols("", manager)
    ids = [s.name.split(" \u2014 ")[0] for s in result]
    assert any(i.startswith("REQ_") for i in ids)
    assert any(i.startswith("SVC_") for i in ids)


def test_workspace_symbols_query_filters(project):
    manager = _MockWorkspaceManager([project])
    result = handle_workspace_symbols("REQ_010", manager)
    assert all("REQ_010" in s.name for s in result)


def test_workspace_symbols_query_no_match(project):
    manager = _MockWorkspaceManager([project])
    result = handle_workspace_symbols("ZZZNOMATCH", manager)
    assert result == []


def test_workspace_symbols_name_format(project):
    manager = _MockWorkspaceManager([project])
    result = handle_workspace_symbols("REQ_010", manager)
    assert result
    assert " \u2014 " in result[0].name
