# Copyright © LFV

from lsprotocol import types

from reqstool.lsp.features.document_symbols import (
    handle_document_symbols,
    _parse_yaml_items,
)


# -- YAML item parsing --


def test_parse_yaml_items_requirements():
    text = (
        "requirements:\n"
        "  - id: REQ_001\n"
        "    title: First requirement\n"
        "    significance: shall\n"
        "  - id: REQ_002\n"
        "    title: Second requirement\n"
        "    significance: should\n"
    )
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 2
    assert items[0].fields["id"] == "REQ_001"
    assert items[0].fields["title"] == "First requirement"
    assert items[0].fields["significance"] == "shall"
    assert items[1].fields["id"] == "REQ_002"


def test_parse_yaml_items_svcs():
    text = "cases:\n" "  - id: SVC_001\n" "    title: Test case\n" "    verification: automated-test\n"
    items = _parse_yaml_items(text, "cases")
    assert len(items) == 1
    assert items[0].fields["id"] == "SVC_001"
    assert items[0].fields["verification"] == "automated-test"


def test_parse_yaml_items_empty():
    text = "metadata:\n  urn: test\n"
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 0


def test_parse_yaml_items_with_metadata():
    text = (
        "metadata:\n"
        "  urn: test\n"
        "  variant: microservice\n"
        "requirements:\n"
        "  - id: REQ_001\n"
        "    title: Test\n"
    )
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 1
    assert items[0].fields["id"] == "REQ_001"


def test_parse_yaml_items_ignores_other_sections():
    """Items in sections other than collection_key must not be returned."""
    text = (
        "metadata:\n"
        "  urn: test\n"
        "implementations:\n"
        "  local:\n"
        "    - path: ../other/reqstool\n"
        "    - path: ../another/reqstool\n"
        "requirements:\n"
        "  - id: REQ_001\n"
        "    title: Real requirement\n"
        "    significance: shall\n"
    )
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 1
    assert items[0].fields["id"] == "REQ_001"


def test_parse_yaml_items_filter_only_file_returns_empty():
    """A filter-only file with no requirements section produces no items."""
    text = (
        "metadata:\n"
        "  urn: atunko-core\n"
        "  variant: microservice\n"
        "\n"
        "implementations:\n"
        "  local:\n"
        "    - path: ../../../docs/reqstool\n"
        "\n"
        "filters:\n"
        "  atunko:\n"
        "    custom:\n"
        "      includes: ids == /CORE_.*/\n"
    )
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 0


def test_parse_yaml_items_imports_section_does_not_pollute():
    """The implementations/imports list items must not appear as requirement items."""
    text = (
        "implementations:\n"
        "  local:\n"
        "    - path: ../../atunko-core/docs/reqstool\n"
        "    - path: ../../atunko-cli/docs/reqstool\n"
        "    - path: ../../atunko-tui/docs/reqstool\n"
        "    - path: ../../atunko-web/docs/reqstool\n"
        "\n"
        "requirements:\n"
        "  - id: WEB_0001\n"
        "    title: Web UI Launch\n"
        "    significance: shall\n"
        "  - id: WEB_0001.1\n"
        "    title: Web UI — Recipe TreeGrid\n"
        "    significance: shall\n"
    )
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 2
    assert items[0].fields["id"] == "WEB_0001"
    assert items[1].fields["id"] == "WEB_0001.1"
    for item in items:
        assert item.fields["id"] != ""
        assert "path" not in item.fields


# -- Document symbols --


def test_document_symbols_requirements():
    text = (
        "requirements:\n"
        "  - id: REQ_001\n"
        "    title: First requirement\n"
        "    significance: shall\n"
        "  - id: REQ_002\n"
        "    title: Second requirement\n"
        "    significance: should\n"
    )
    symbols = handle_document_symbols(
        uri="file:///workspace/requirements.yml",
        text=text,
        project=None,
    )
    assert len(symbols) == 2
    assert "REQ_001" in symbols[0].name
    assert "First requirement" in symbols[0].name
    assert symbols[0].detail == "shall"
    assert "REQ_002" in symbols[1].name
    assert symbols[1].detail == "should"


def test_document_symbols_svcs():
    text = "cases:\n" "  - id: SVC_001\n" "    title: Login test\n" "    verification: automated-test\n"
    symbols = handle_document_symbols(
        uri="file:///workspace/software_verification_cases.yml",
        text=text,
        project=None,
    )
    assert len(symbols) == 1
    assert "SVC_001" in symbols[0].name
    assert symbols[0].detail == "automated-test"


def test_document_symbols_mvrs():
    text = "results:\n" "  - id: SVC_001\n" "    passed: true\n" "  - id: SVC_002\n" "    passed: false\n"
    symbols = handle_document_symbols(
        uri="file:///workspace/manual_verification_results.yml",
        text=text,
        project=None,
    )
    assert len(symbols) == 2
    assert "SVC_001" in symbols[0].name
    assert "pass" in symbols[0].name
    assert "SVC_002" in symbols[1].name
    assert "fail" in symbols[1].name


def test_document_symbols_non_reqstool_file():
    text = "key: value\n"
    symbols = handle_document_symbols(
        uri="file:///workspace/other.yml",
        text=text,
        project=None,
    )
    assert symbols == []


def test_document_symbols_empty():
    text = ""
    symbols = handle_document_symbols(
        uri="file:///workspace/requirements.yml",
        text=text,
        project=None,
    )
    assert symbols == []


def test_document_symbols_filter_only_file_is_empty():
    """A requirements.yml with only metadata/imports/filters produces no symbols."""
    text = (
        "metadata:\n"
        "  urn: atunko-core\n"
        "  variant: microservice\n"
        "\n"
        "implementations:\n"
        "  local:\n"
        "    - path: ../../../docs/reqstool\n"
        "\n"
        "filters:\n"
        "  atunko:\n"
        "    custom:\n"
        "      includes: ids == /CORE_.*/\n"
    )
    symbols = handle_document_symbols(
        uri="file:///workspace/requirements.yml",
        text=text,
        project=None,
    )
    assert symbols == []


def test_document_symbols_no_empty_names():
    """No symbol produced by handle_document_symbols should have an empty name."""
    text = (
        "implementations:\n"
        "  local:\n"
        "    - path: ../../atunko-core/docs/reqstool\n"
        "    - path: ../../atunko-web/docs/reqstool\n"
        "\n"
        "requirements:\n"
        "  - id: WEB_0001\n"
        "    title: Web UI Launch\n"
        "    significance: shall\n"
        "  - id: WEB_0001.1\n"
        "    title: Web UI — Recipe TreeGrid\n"
        "    significance: shall\n"
    )
    symbols = handle_document_symbols(
        uri="file:///workspace/requirements.yml",
        text=text,
        project=None,
    )
    assert len(symbols) == 2
    for sym in symbols:
        assert sym.name, f"Symbol at line {sym.range.start.line} has an empty name"


def test_document_symbols_with_project(local_testdata_resources_rootdir_w_path):
    """Test that symbols include children when project is loaded."""
    import os

    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        req_file = os.path.join(path, "requirements.yml")
        if os.path.isfile(req_file):
            with open(req_file) as f:
                text = f.read()
            symbols = handle_document_symbols(
                uri="file://" + req_file,
                text=text,
                project=state,
            )
            assert len(symbols) > 0
            # Symbols should be DocumentSymbol instances with non-empty names
            for sym in symbols:
                assert isinstance(sym, types.DocumentSymbol)
                assert sym.kind == types.SymbolKind.Key
                assert sym.name, f"Symbol at line {sym.range.start.line} has an empty name"
    finally:
        state.close()


def test_parse_yaml_items_line_ranges():
    text = (
        "requirements:\n"
        "  - id: REQ_001\n"
        "    title: Test\n"
        "    significance: shall\n"
        "  - id: REQ_002\n"
        "    title: Second\n"
    )
    items = _parse_yaml_items(text, "requirements")
    assert len(items) == 2
    assert items[0].start_line == 1
    assert items[0].id_line == 1
    assert items[1].start_line == 4
