# Copyright © LFV

import pytest

from reqstool.lsp.features.semantic_tokens import TOKEN_TYPES, _encode_tokens, handle_semantic_tokens
from reqstool.lsp.project_state import ProjectState

URI = "file:///test.py"


def test_encode_tokens_empty():
    assert _encode_tokens([]) == []


def test_encode_tokens_single():
    data = _encode_tokens([(3, 5, 6, 1)])
    assert data == [3, 5, 6, 1, 0]


def test_encode_tokens_same_line():
    # Two tokens on the same line: delta_start is relative to previous token start
    data = _encode_tokens([(1, 2, 4, 0), (1, 10, 6, 1)])
    assert data == [1, 2, 4, 0, 0, 0, 8, 6, 1, 0]


def test_encode_tokens_different_lines():
    data = _encode_tokens([(0, 5, 3, 0), (2, 7, 4, 1)])
    assert data == [0, 5, 3, 0, 0, 2, 7, 4, 1, 0]


def test_encode_tokens_sorted():
    # Input out of order — must be sorted by line then col
    data = _encode_tokens([(2, 0, 3, 0), (0, 0, 3, 1)])
    assert data[0] == 0  # first token is line 0
    assert data[5] == 2  # second token delta line is 2


def test_token_types_count():
    assert len(TOKEN_TYPES) == 4


def test_token_types_order():
    assert TOKEN_TYPES[0] == "reqstoolDraft"
    assert TOKEN_TYPES[1] == "reqstoolValid"
    assert TOKEN_TYPES[2] == "reqstoolDeprecated"
    assert TOKEN_TYPES[3] == "reqstoolObsolete"


def test_state_to_idx_all_distinct():
    from reqstool.lsp.features.semantic_tokens import _STATE_TO_IDX
    from reqstool.common.models.lifecycle import LIFECYCLESTATE

    assert _STATE_TO_IDX[LIFECYCLESTATE.DRAFT] == 0
    assert _STATE_TO_IDX[LIFECYCLESTATE.EFFECTIVE] == 1
    assert _STATE_TO_IDX[LIFECYCLESTATE.DEPRECATED] == 2
    assert _STATE_TO_IDX[LIFECYCLESTATE.OBSOLETE] == 3
    assert len(set(_STATE_TO_IDX.values())) == 4  # all indices distinct


def test_semantic_tokens_no_project():
    result = handle_semantic_tokens(URI, '@Requirements("REQ_010")', "python", None)
    assert result.data == []


def test_semantic_tokens_project_not_ready():
    state = ProjectState(reqstool_path="/nonexistent")
    result = handle_semantic_tokens(URI, '@Requirements("REQ_010")', "python", state)
    assert result.data == []


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_semantic_tokens_known_id(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_semantic_tokens(URI, text, "python", project)
    # Should produce 5 integers per token
    assert len(result.data) % 5 == 0
    assert len(result.data) >= 5


def test_semantic_tokens_unknown_id(project):
    text = '@Requirements("REQ_NONEXISTENT")\ndef foo(): pass'
    result = handle_semantic_tokens(URI, text, "python", project)
    # Unknown IDs get type_idx 0 (effective fallback)
    assert len(result.data) % 5 == 0
    assert len(result.data) >= 5
