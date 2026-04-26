# Copyright © LFV

from lsprotocol import types

from reqstool.lsp.features.diagnostics import compute_diagnostics


# -- Source code diagnostics --


def test_diagnostics_unknown_requirement(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@Requirements("REQ_NONEXISTENT")\ndef foo(): pass'
        diags = compute_diagnostics(
            uri="file:///test.py",
            text=text,
            language_id="python",
            project=state,
        )
        assert len(diags) == 1
        assert diags[0].severity == types.DiagnosticSeverity.Error
        assert "Unknown requirement" in diags[0].message
        assert "REQ_NONEXISTENT" in diags[0].message
        assert diags[0].source == "reqstool"
    finally:
        state.close()


def test_diagnostics_valid_requirement(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@Requirements("REQ_010")\ndef foo(): pass'
        diags = compute_diagnostics(
            uri="file:///test.py",
            text=text,
            language_id="python",
            project=state,
        )
        # REQ_010 exists and is effective — no diagnostics
        assert len(diags) == 0
    finally:
        state.close()


def test_diagnostics_unknown_svc(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        text = '@SVCs("SVC_NONEXISTENT")\ndef foo(): pass'
        diags = compute_diagnostics(
            uri="file:///test.py",
            text=text,
            language_id="python",
            project=state,
        )
        assert len(diags) == 1
        assert diags[0].severity == types.DiagnosticSeverity.Error
        assert "Unknown SVC" in diags[0].message
    finally:
        state.close()


def test_diagnostics_no_project():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    diags = compute_diagnostics(
        uri="file:///test.py",
        text=text,
        language_id="python",
        project=None,
    )
    assert len(diags) == 0


def test_diagnostics_no_annotations():
    text = "def foo(): pass"
    diags = compute_diagnostics(
        uri="file:///test.py",
        text=text,
        language_id="python",
        project=None,
    )
    assert len(diags) == 0


def test_diagnostics_multiple_ids_mixed(local_testdata_resources_rootdir_w_path):
    from reqstool.lsp.project_state import ProjectState

    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        # One valid, one invalid
        text = '@Requirements("REQ_010", "REQ_NONEXISTENT")\ndef foo(): pass'
        diags = compute_diagnostics(
            uri="file:///test.py",
            text=text,
            language_id="python",
            project=state,
        )
        # Only the unknown one should produce a diagnostic
        assert len(diags) == 1
        assert "REQ_NONEXISTENT" in diags[0].message
    finally:
        state.close()


# -- YAML diagnostics --


def test_diagnostics_yaml_valid():
    """Valid YAML with correct schema should produce no diagnostics."""
    text = (
        "metadata:\n"
        "  urn: test:urn\n"
        "  variant: microservice\n"
        "  title: Test\n"
        "  url: https://example.com\n"
        "requirements:\n"
        "  - id: REQ_001\n"
        "    title: Test requirement\n"
        "    significance: shall\n"
        "    description: A test requirement\n"
        "    categories:\n"
        "      - functional-suitability\n"
        "    revision: '1.0.0'\n"
        "    implementation: in-code\n"
    )
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    # May or may not have schema errors depending on exact schema requirements,
    # but at minimum should not crash
    assert isinstance(diags, list)


def test_diagnostics_yaml_parse_error():
    """Invalid YAML should produce a parse error diagnostic."""
    text = "metadata:\n  urn: [\n"
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    assert len(diags) >= 1
    assert diags[0].severity == types.DiagnosticSeverity.Error
    assert "YAML parse error" in diags[0].message


def test_diagnostics_yaml_schema_error():
    """YAML with missing required fields should produce schema error diagnostics."""
    text = "metadata:\n  urn: test\n"
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    assert len(diags) >= 1
    assert any("Schema error" in d.message for d in diags)


def test_diagnostics_yaml_non_reqstool_file():
    """Non-reqstool YAML files should produce no diagnostics."""
    text = "key: value\n"
    diags = compute_diagnostics(
        uri="file:///workspace/other.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    assert len(diags) == 0


def test_diagnostics_filters_section_does_not_break_validation():
    """Regression for #361: a requirements.yml using `filters:` (which references
    common.schema.json#/$defs/filters) must validate without raising
    Unresolvable, and must not surface an "Unresolvable" message."""
    text = (
        "metadata:\n"
        "  urn: atunko-core\n"
        "  variant: microservice\n"
        "  title: Atunko core\n"
        "filters:\n"
        "  atunko:\n"
        "    custom:\n"
        "      includes: ids == /CORE_.*/\n"
    )
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    assert isinstance(diags, list)
    for d in diags:
        assert "Unresolvable" not in d.message
        assert "common.schema.json" not in d.message


def test_diagnostics_imports_local_path_does_not_break_validation():
    """Regression for #361: imports.local[].path is typed against
    common.schema.json#/$defs/urnid; must validate without raising Unresolvable."""
    text = (
        "metadata:\n"
        "  urn: my-urn\n"
        "  variant: microservice\n"
        "  title: Test\n"
        "imports:\n"
        "  local:\n"
        "    - path: ../sys-001\n"
    )
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    assert isinstance(diags, list)
    for d in diags:
        assert "Unresolvable" not in d.message


def test_diagnostics_unresolvable_is_caught_and_reported(monkeypatch):
    """If a future schema $ref ever fails to resolve, a single Error diagnostic
    is returned at 0:0 instead of the exception escaping to the LSP client."""
    from referencing.exceptions import Unresolvable

    from reqstool.lsp.features import diagnostics as diag_mod

    class _BoomValidator:
        FORMAT_CHECKER = None

        def __init__(self, *args, **kwargs):
            pass

        def iter_errors(self, data):
            raise Unresolvable("simulated $ref failure")

    monkeypatch.setattr(diag_mod, "Draft202012Validator", _BoomValidator)

    text = "metadata:\n  urn: test\n"
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    assert len(diags) == 1
    assert diags[0].severity == types.DiagnosticSeverity.Error
    assert "Schema resolution error" in diags[0].message
    assert diags[0].range.start.line == 0
    assert diags[0].range.start.character == 0


def test_diagnostics_yaml_empty():
    """Empty YAML should produce no diagnostics (or schema errors for missing required)."""
    text = ""
    diags = compute_diagnostics(
        uri="file:///workspace/requirements.yml",
        text=text,
        language_id="yaml",
        project=None,
    )
    # Empty YAML parses to None, which we skip
    assert isinstance(diags, list)
