# Copyright © LFV

from lsprotocol import types

from reqstool.lsp.features.hover import handle_hover, _yaml_field_path_at_line


# -- Source code hover --


def test_hover_python_requirement(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@Requirements("REQ_010")\ndef foo(): pass'
        result = handle_hover(
            uri="file:///test.py",
            position=types.Position(line=0, character=17),
            text=text,
            language_id="python",
            project=state,
        )
        assert result is not None
        assert "REQ_010" in result.contents.value
        assert "Title REQ_010" in result.contents.value
        assert "Implementations" in result.contents.value
    finally:
        state.close()


def test_hover_python_svc_test_summary(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        svc_ids = state.get_all_svc_ids()
        assert svc_ids
        text = f'@SVCs("{svc_ids[0]}")\ndef test_foo(): pass'
        result = handle_hover(
            uri="file:///test.py",
            position=types.Position(line=0, character=8),
            text=text,
            language_id="python",
            project=state,
        )
        assert result is not None
        assert "Tests" in result.contents.value
        assert "MVRs" in result.contents.value
        assert "passed" in result.contents.value
    finally:
        state.close()


def test_hover_python_unknown_id(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@Requirements("REQ_NONEXISTENT")\ndef foo(): pass'
        result = handle_hover(
            uri="file:///test.py",
            position=types.Position(line=0, character=17),
            text=text,
            language_id="python",
            project=state,
        )
        assert result is not None
        assert "Unknown" in result.contents.value
    finally:
        state.close()


def test_hover_no_project():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_hover(
        uri="file:///test.py",
        position=types.Position(line=0, character=17),
        text=text,
        language_id="python",
        project=None,
    )
    assert result is not None
    assert "not loaded" in result.contents.value


def test_hover_outside_annotation():
    text = "def foo(): pass"
    result = handle_hover(
        uri="file:///test.py",
        position=types.Position(line=0, character=5),
        text=text,
        language_id="python",
        project=None,
    )
    assert result is None


# -- YAML hover --


def test_hover_yaml_field():
    text = "metadata:\n  urn: my-urn\n  variant: system\n  title: My Title\n"
    result = handle_hover(
        uri="file:///workspace/requirements.yml",
        position=types.Position(line=2, character=3),
        text=text,
        language_id="yaml",
        project=None,
    )
    assert result is not None
    assert "variant" in result.contents.value


def test_hover_yaml_significance():
    text = "requirements:\n  - id: REQ_001\n    significance: shall\n"
    result = handle_hover(
        uri="file:///workspace/requirements.yml",
        position=types.Position(line=2, character=5),
        text=text,
        language_id="yaml",
        project=None,
    )
    assert result is not None
    assert "significance" in result.contents.value


def test_hover_yaml_non_reqstool_file():
    text = "key: value\n"
    result = handle_hover(
        uri="file:///workspace/some_other.yml",
        position=types.Position(line=0, character=1),
        text=text,
        language_id="yaml",
        project=None,
    )
    assert result is None


# -- YAML field path parsing --


def test_yaml_field_path_simple():
    text = "metadata:\n  urn: value"
    path = _yaml_field_path_at_line(text, 1)
    assert path == ["metadata", "urn"]


def test_yaml_field_path_top_level():
    text = "metadata:\n  urn: value"
    path = _yaml_field_path_at_line(text, 0)
    assert path == ["metadata"]


def test_yaml_field_path_nested():
    text = "metadata:\n  urn: value\n  variant: system\nrequirements:\n  - id: REQ_001\n    significance: shall"
    path = _yaml_field_path_at_line(text, 5)
    assert path == ["requirements", "significance"]


def test_yaml_field_path_no_field():
    text = "  - some list item"
    path = _yaml_field_path_at_line(text, 0)
    assert path == []
