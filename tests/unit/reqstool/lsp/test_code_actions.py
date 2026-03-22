# Copyright © LFV

import pytest
from lsprotocol import types

from reqstool.lsp.features.code_actions import handle_code_actions
from reqstool.lsp.project_state import ProjectState

URI = "file:///test.py"
EMPTY_RANGE = types.Range(
    start=types.Position(line=0, character=0),
    end=types.Position(line=0, character=0),
)


def _context(diagnostics=None, only=None):
    return types.CodeActionContext(
        diagnostics=diagnostics or [],
        only=only,
    )


def test_code_actions_no_diagnostics_no_annotation():
    result = handle_code_actions(URI, EMPTY_RANGE, _context(), "def foo(): pass", "python", None)
    assert result == []


def test_code_actions_unknown_requirement_diagnostic():
    diag = types.Diagnostic(
        range=EMPTY_RANGE,
        severity=types.DiagnosticSeverity.Error,
        source="reqstool",
        message="Unknown requirement: REQ_UNKNOWN",
    )
    result = handle_code_actions(URI, EMPTY_RANGE, _context([diag]), "", "python", None)
    assert len(result) == 1
    assert result[0].kind == types.CodeActionKind.QuickFix
    assert "REQ_UNKNOWN" in result[0].title
    assert result[0].command.command == "reqstool.openDetails"
    assert result[0].command.arguments[0]["type"] == "requirement"


def test_code_actions_unknown_svc_diagnostic():
    diag = types.Diagnostic(
        range=EMPTY_RANGE,
        severity=types.DiagnosticSeverity.Error,
        source="reqstool",
        message="Unknown SVC: SVC_UNKNOWN",
    )
    result = handle_code_actions(URI, EMPTY_RANGE, _context([diag]), "", "python", None)
    assert len(result) == 1
    assert result[0].command.arguments[0]["type"] == "svc"


def test_code_actions_deprecated_diagnostic():
    diag = types.Diagnostic(
        range=EMPTY_RANGE,
        severity=types.DiagnosticSeverity.Warning,
        source="reqstool",
        message="Requirement REQ_010 is deprecated: old",
    )
    result = handle_code_actions(URI, EMPTY_RANGE, _context([diag]), "", "python", None)
    assert len(result) == 1
    assert result[0].kind == types.CodeActionKind.QuickFix
    assert "REQ_010" in result[0].title


def test_code_actions_ignores_non_reqstool_diagnostics():
    diag = types.Diagnostic(
        range=EMPTY_RANGE,
        severity=types.DiagnosticSeverity.Error,
        source="pylint",
        message="Unknown requirement: REQ_010",
    )
    result = handle_code_actions(URI, EMPTY_RANGE, _context([diag]), "", "python", None)
    assert result == []


def test_code_actions_only_quickfix_filter():
    diag = types.Diagnostic(
        range=EMPTY_RANGE,
        severity=types.DiagnosticSeverity.Error,
        source="reqstool",
        message="Unknown requirement: REQ_UNKNOWN",
    )
    result = handle_code_actions(
        URI, EMPTY_RANGE, _context([diag], only=[types.CodeActionKind.QuickFix]), "", "python", None
    )
    assert all(a.kind == types.CodeActionKind.QuickFix for a in result)


@pytest.fixture
def project(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    yield state
    state.close()


def test_code_actions_source_action_on_known_id(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    cursor_range = types.Range(
        start=types.Position(line=0, character=17),
        end=types.Position(line=0, character=24),
    )
    result = handle_code_actions(URI, cursor_range, _context(), text, "python", project)
    source_actions = [a for a in result if a.kind == types.CodeActionKind.Source]
    assert source_actions
    assert source_actions[0].command.arguments[0]["type"] == "requirement"


def test_code_actions_source_action_only_filter(project):
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    cursor_range = types.Range(
        start=types.Position(line=0, character=17),
        end=types.Position(line=0, character=24),
    )
    result = handle_code_actions(
        URI, cursor_range, _context(only=[types.CodeActionKind.QuickFix]), text, "python", project
    )
    # Source actions should be filtered out
    assert all(a.kind != types.CodeActionKind.Source for a in result)
