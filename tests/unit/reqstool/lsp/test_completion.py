# Copyright © LFV

from lsprotocol import types

from reqstool.lsp.features.completion import handle_completion, _yaml_value_context


# -- Source code completion --


def test_completion_requirements(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@Requirements("'
        result = handle_completion(
            uri="file:///test.py",
            position=types.Position(line=0, character=16),
            text=text,
            language_id="python",
            project=state,
        )
        assert result is not None
        assert len(result.items) > 0
        labels = [item.label for item in result.items]
        assert "REQ_010" in labels
    finally:
        state.close()


def test_completion_svcs(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@SVCs("'
        result = handle_completion(
            uri="file:///test.py",
            position=types.Position(line=0, character=7),
            text=text,
            language_id="python",
            project=state,
        )
        assert result is not None
        assert len(result.items) > 0
        # All items should be SVC IDs
        for item in result.items:
            assert item.kind == types.CompletionItemKind.Reference
    finally:
        state.close()


def test_completion_no_project():
    text = '@Requirements("'
    result = handle_completion(
        uri="file:///test.py",
        position=types.Position(line=0, character=16),
        text=text,
        language_id="python",
        project=None,
    )
    assert result is None


def test_completion_outside_annotation():
    text = "def foo(): pass"
    result = handle_completion(
        uri="file:///test.py",
        position=types.Position(line=0, character=5),
        text=text,
        language_id="python",
        project=None,
    )
    assert result is None


# -- YAML completion --


def test_completion_yaml_significance():
    text = "requirements:\n  - id: REQ_001\n    significance: "
    result = handle_completion(
        uri="file:///workspace/requirements.yml",
        position=types.Position(line=2, character=20),
        text=text,
        language_id="yaml",
        project=None,
    )
    assert result is not None
    labels = [item.label for item in result.items]
    assert "shall" in labels
    assert "should" in labels
    assert "may" in labels


def test_completion_yaml_variant():
    text = "metadata:\n  variant: "
    result = handle_completion(
        uri="file:///workspace/requirements.yml",
        position=types.Position(line=1, character=12),
        text=text,
        language_id="yaml",
        project=None,
    )
    assert result is not None
    labels = [item.label for item in result.items]
    assert "microservice" in labels
    assert "system" in labels
    assert "external" in labels


def test_completion_yaml_non_enum_field():
    text = "metadata:\n  urn: "
    result = handle_completion(
        uri="file:///workspace/requirements.yml",
        position=types.Position(line=1, character=7),
        text=text,
        language_id="yaml",
        project=None,
    )
    # urn is not an enum field, no completion
    assert result is None


def test_completion_yaml_non_reqstool_file():
    text = "key: value\n"
    result = handle_completion(
        uri="file:///workspace/other.yml",
        position=types.Position(line=0, character=5),
        text=text,
        language_id="yaml",
        project=None,
    )
    assert result is None


# -- YAML value context --


def test_yaml_value_context_simple():
    text = "metadata:\n  variant: "
    path = _yaml_value_context(text, 1)
    assert path == ["metadata", "variant"]


def test_yaml_value_context_array_item():
    text = "requirements:\n  - id: REQ_001\n    significance: "
    path = _yaml_value_context(text, 2)
    assert path == ["requirements", "significance"]


def test_yaml_value_context_top_level():
    text = "metadata:\n  urn: value"
    path = _yaml_value_context(text, 0)
    assert path == ["metadata"]


def test_yaml_value_context_no_field():
    text = "  - some list item"
    path = _yaml_value_context(text, 0)
    assert path is None
