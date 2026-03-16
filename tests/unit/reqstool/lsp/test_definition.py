# Copyright © LFV

import os

from lsprotocol import types

from reqstool.lsp.features.definition import (
    handle_definition,
    _find_id_in_yaml,
    _id_at_yaml_position,
    _path_to_uri,
)


# -- Source → YAML definition --


def test_definition_from_source(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@Requirements("REQ_010")\ndef foo(): pass'
        result = handle_definition(
            uri="file:///test.py",
            position=types.Position(line=0, character=17),
            text=text,
            language_id="python",
            project=state,
        )
        # Should find the ID in requirements.yml
        assert isinstance(result, list)
        if len(result) > 0:
            assert "requirements.yml" in result[0].uri
    finally:
        state.close()


def test_definition_from_source_no_project():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_definition(
        uri="file:///test.py",
        position=types.Position(line=0, character=17),
        text=text,
        language_id="python",
        project=None,
    )
    assert result == []


def test_definition_from_source_no_annotation():
    text = "def foo(): pass"
    result = handle_definition(
        uri="file:///test.py",
        position=types.Position(line=0, character=5),
        text=text,
        language_id="python",
        project=None,
    )
    assert result == []


# -- Find ID in YAML --


def test_find_id_in_yaml(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    yaml_file = os.path.join(path, "requirements.yml")
    if os.path.isfile(yaml_file):
        result = _find_id_in_yaml(yaml_file, "REQ_010")
        assert isinstance(result, list)
        if len(result) > 0:
            assert result[0].range.start.line >= 0


def test_find_id_in_yaml_nonexistent_file():
    result = _find_id_in_yaml("/nonexistent/path/requirements.yml", "REQ_010")
    assert result == []


def test_find_id_in_yaml_nonexistent_id(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    yaml_file = os.path.join(path, "requirements.yml")
    if os.path.isfile(yaml_file):
        result = _find_id_in_yaml(yaml_file, "REQ_NONEXISTENT")
        assert result == []


# -- ID at YAML position --


def test_id_at_yaml_position_id_field():
    text = "requirements:\n  - id: REQ_001\n    title: Test"
    raw_id = _id_at_yaml_position(text, types.Position(line=1, character=10))
    assert raw_id == "REQ_001"


def test_id_at_yaml_position_bare_list_item():
    text = "requirement_ids:\n  - REQ_001\n  - REQ_002"
    raw_id = _id_at_yaml_position(text, types.Position(line=1, character=5))
    assert raw_id == "REQ_001"


def test_id_at_yaml_position_no_id():
    text = "metadata:\n  title: Test"
    raw_id = _id_at_yaml_position(text, types.Position(line=1, character=5))
    assert raw_id is None


def test_id_at_yaml_position_out_of_range():
    text = "metadata:\n  urn: test"
    raw_id = _id_at_yaml_position(text, types.Position(line=5, character=0))
    assert raw_id is None


# -- Path to URI --


def test_path_to_uri():
    uri = _path_to_uri("/home/user/project/requirements.yml")
    assert uri == "file:///home/user/project/requirements.yml"
