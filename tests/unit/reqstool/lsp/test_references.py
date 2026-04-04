# Copyright © LFV

import pytest
from lsprotocol import types

from reqstool.lsp.features.references import handle_references
from reqstool.lsp.project_state import ProjectState

URI = "file:///test.py"


def _make_doc(source, language_id="python"):
    class _Doc:
        pass

    doc = _Doc()
    doc.source = source
    doc.language_id = language_id
    return doc


def test_references_no_project():
    result = handle_references(
        URI, types.Position(line=0, character=17), '@Requirements("REQ_010")', "python", None, True, {}
    )
    assert result == []


def test_references_no_id_at_cursor():
    result = handle_references(URI, types.Position(line=0, character=0), "def foo(): pass", "python", None, True, {})
    assert result == []


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_references_finds_open_document(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    open_docs = {URI: _make_doc(text)}
    result = handle_references(URI, types.Position(line=0, character=17), text, "python", project, True, open_docs)
    assert any(loc.uri == URI for loc in result)


def test_references_finds_yaml_files(project):
    # Cursor on REQ_010 in source; YAML files for the project should also be searched
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = handle_references(URI, types.Position(line=0, character=17), text, "python", project, True, {})
    yaml_locations = [loc for loc in result if loc.uri.endswith(".yml")]
    assert yaml_locations, "Expected at least one YAML reference location"


def test_references_exclude_declaration(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    with_decl = handle_references(URI, types.Position(line=0, character=17), text, "python", project, True, {})
    without_decl = handle_references(URI, types.Position(line=0, character=17), text, "python", project, False, {})
    # Excluding declarations should produce fewer or equal results
    assert len(without_decl) <= len(with_decl)
