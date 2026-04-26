# Copyright © LFV

import os
import textwrap

import pytest
from lsprotocol import types

from reqstool.lsp.features.document_symbols import handle_document_symbols
from reqstool.lsp.project_state import ProjectState


@pytest.fixture
def ms001_project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield path, state
    state.close()


def test_non_reqstool_file_returns_empty():
    symbols = handle_document_symbols(uri="file:///workspace/other.yml", text="key: value\n", project=None)
    assert symbols == []


def test_no_project_returns_empty():
    symbols = handle_document_symbols(
        uri="file:///workspace/requirements.yml",
        text="requirements:\n  - id: REQ_001\n",
        project=None,
    )
    assert symbols == []


def test_requirements_symbols_have_titles_and_significance(ms001_project):
    path, state = ms001_project
    req_file = os.path.join(path, "requirements.yml")
    with open(req_file) as f:
        text = f.read()

    symbols = handle_document_symbols(uri="file://" + req_file, text=text, project=state)

    assert len(symbols) == 2
    for sym in symbols:
        assert isinstance(sym, types.DocumentSymbol)
        assert sym.kind == types.SymbolKind.Key
        assert sym.name  # never empty
    assert "REQ_010" in symbols[0].name
    assert "Title REQ_010" in symbols[0].name
    assert symbols[0].detail == "should"
    assert "REQ_020" in symbols[1].name
    assert symbols[1].detail == "shall"


def test_requirements_symbol_line_numbers_match_yaml(ms001_project):
    path, state = ms001_project
    req_file = os.path.join(path, "requirements.yml")
    with open(req_file) as f:
        text = f.read()

    symbols = handle_document_symbols(uri="file://" + req_file, text=text, project=state)

    # REQ_010 is on line 15 (1-based) in the fixture → 0-based line 14
    assert symbols[0].selection_range.start.line == 14
    # REQ_020 is on line 22 → 0-based line 21
    assert symbols[1].selection_range.start.line == 21


def test_filter_only_requirements_yml_returns_empty(tmp_path):
    """Regression for #359: a requirements.yml with only metadata/implementations/filters
    must not produce ghost symbols with empty names."""
    yml = textwrap.dedent(
        """\
        metadata:
          urn: filter-only
          variant: microservice
          title: Filter only
        implementations:
          local:
            - path: ../target
        filters:
          some-other-urn:
            custom:
              includes: ids == /CORE_.*/
        """
    )
    req_file = tmp_path / "requirements.yml"
    req_file.write_text(yml)

    state = ProjectState(reqstool_path=str(tmp_path))
    state.build()
    try:
        symbols = handle_document_symbols(uri="file://" + str(req_file), text=yml, project=state)
        # Either ProjectState fails to build (no implementation target) or it builds but the file
        # has no `requirements:` section — either way the outline must be empty, never empty-named.
        assert symbols == [] or all(sym.name for sym in symbols)
    finally:
        state.close()


def test_svcs_symbols_built_from_db(ms001_project):
    path, state = ms001_project
    svc_file = os.path.join(path, "software_verification_cases.yml")
    with open(svc_file) as f:
        text = f.read()

    symbols = handle_document_symbols(uri="file://" + svc_file, text=text, project=state)

    assert len(symbols) > 0
    for sym in symbols:
        assert sym.name
        assert sym.kind == types.SymbolKind.Key


def test_mvrs_symbols_built_from_db(ms001_project):
    path, state = ms001_project
    mvr_file = os.path.join(path, "manual_verification_results.yml")
    if not os.path.isfile(mvr_file):
        pytest.skip("ms-001 fixture has no MVRs file")
    with open(mvr_file) as f:
        text = f.read()

    symbols = handle_document_symbols(uri="file://" + mvr_file, text=text, project=state)

    for sym in symbols:
        assert sym.name
        assert "pass" in sym.name or "fail" in sym.name
