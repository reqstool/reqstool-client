# Copyright © LFV

import pytest
from lsprotocol import types

from reqstool.lsp.features.inlay_hints import handle_inlay_hints
from reqstool.lsp.project_state import ProjectState

URI = "file:///test.py"
FULL_RANGE = types.Range(
    start=types.Position(line=0, character=0),
    end=types.Position(line=999, character=0),
)


def test_inlay_hints_no_project():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_inlay_hints(URI, FULL_RANGE, text, "python", None)
    assert result == []


def test_inlay_hints_project_not_ready():
    state = ProjectState(reqstool_path="/nonexistent")
    result = handle_inlay_hints(URI, FULL_RANGE, '@Requirements("REQ_010")', "python", state)
    assert result == []


def test_inlay_hints_no_annotations():
    result = handle_inlay_hints(URI, FULL_RANGE, "def foo(): pass", "python", None)
    assert result == []


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_inlay_hints_known_id(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_inlay_hints(URI, FULL_RANGE, text, "python", project)
    assert len(result) == 1
    hint = result[0]
    assert "\u2190" in hint.label
    assert hint.kind == types.InlayHintKind.Type


def test_inlay_hints_unknown_id_skipped(project):
    text = '@Requirements("REQ_NONEXISTENT")\ndef foo(): pass'
    result = handle_inlay_hints(URI, FULL_RANGE, text, "python", project)
    assert result == []


def test_inlay_hints_range_filter(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass\n@Requirements("REQ_010")\ndef bar(): pass'
    narrow_range = types.Range(
        start=types.Position(line=2, character=0),
        end=types.Position(line=3, character=0),
    )
    result = handle_inlay_hints(URI, narrow_range, text, "python", project)
    # Only the annotation on line 2 is within range
    assert len(result) == 1
    assert result[0].position.line == 2
