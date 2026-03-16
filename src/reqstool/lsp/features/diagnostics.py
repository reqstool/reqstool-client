# Copyright © LFV

from __future__ import annotations

import logging
import os
import re

import yaml
from jsonschema import Draft202012Validator
from lsprotocol import types

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.lsp.annotation_parser import find_all_annotations
from reqstool.lsp.project_state import ProjectState
from reqstool.lsp.yaml_schema import schema_for_yaml_file

logger = logging.getLogger(__name__)

# YAML files that the LSP validates
REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
    "reqstool_config.yml",
}


def compute_diagnostics(
    uri: str,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> list[types.Diagnostic]:
    basename = os.path.basename(uri)
    if basename in REQSTOOL_YAML_FILES:
        return _yaml_diagnostics(text, basename)
    else:
        return _source_diagnostics(text, language_id, project)


def _source_diagnostics(
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> list[types.Diagnostic]:
    if project is None or not project.ready:
        return []

    annotations = find_all_annotations(text, language_id)
    diagnostics: list[types.Diagnostic] = []

    for match in annotations:
        if match.kind == "Requirements":
            req = project.get_requirement(match.raw_id)
            if req is None:
                diagnostics.append(
                    types.Diagnostic(
                        range=types.Range(
                            start=types.Position(line=match.line, character=match.start_col),
                            end=types.Position(line=match.line, character=match.end_col),
                        ),
                        severity=types.DiagnosticSeverity.Error,
                        source="reqstool",
                        message=f"Unknown requirement: {match.raw_id}",
                    )
                )
            else:
                _check_lifecycle(diagnostics, match, req.lifecycle.state, req.lifecycle.reason, "Requirement")

        elif match.kind == "SVCs":
            svc = project.get_svc(match.raw_id)
            if svc is None:
                diagnostics.append(
                    types.Diagnostic(
                        range=types.Range(
                            start=types.Position(line=match.line, character=match.start_col),
                            end=types.Position(line=match.line, character=match.end_col),
                        ),
                        severity=types.DiagnosticSeverity.Error,
                        source="reqstool",
                        message=f"Unknown SVC: {match.raw_id}",
                    )
                )
            else:
                _check_lifecycle(diagnostics, match, svc.lifecycle.state, svc.lifecycle.reason, "SVC")

    return diagnostics


def _check_lifecycle(diagnostics, match, state, reason, kind_label):
    if state == LIFECYCLESTATE.DEPRECATED:
        reason_text = f": {reason}" if reason else ""
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=match.line, character=match.start_col),
                    end=types.Position(line=match.line, character=match.end_col),
                ),
                severity=types.DiagnosticSeverity.Warning,
                source="reqstool",
                message=f"{kind_label} {match.raw_id} is deprecated{reason_text}",
            )
        )
    elif state == LIFECYCLESTATE.OBSOLETE:
        reason_text = f": {reason}" if reason else ""
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=match.line, character=match.start_col),
                    end=types.Position(line=match.line, character=match.end_col),
                ),
                severity=types.DiagnosticSeverity.Warning,
                source="reqstool",
                message=f"{kind_label} {match.raw_id} is obsolete{reason_text}",
            )
        )


def _yaml_diagnostics(text: str, filename: str) -> list[types.Diagnostic]:
    """Validate YAML content against its JSON schema."""
    schema = schema_for_yaml_file(filename)
    if schema is None:
        return []

    # Parse YAML first
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        diag_range = types.Range(
            start=types.Position(line=0, character=0),
            end=types.Position(line=0, character=0),
        )
        if hasattr(e, "problem_mark") and e.problem_mark is not None:
            line = e.problem_mark.line
            col = e.problem_mark.column
            diag_range = types.Range(
                start=types.Position(line=line, character=col),
                end=types.Position(line=line, character=col),
            )
        return [
            types.Diagnostic(
                range=diag_range,
                severity=types.DiagnosticSeverity.Error,
                source="reqstool",
                message=f"YAML parse error: {e}",
            )
        ]

    if data is None:
        return []

    # Validate against JSON schema
    validator = Draft202012Validator(schema)
    diagnostics: list[types.Diagnostic] = []

    for error in validator.iter_errors(data):
        line, col = _find_error_position(text, error)
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=line, character=col),
                    end=types.Position(line=line, character=col),
                ),
                severity=types.DiagnosticSeverity.Error,
                source="reqstool",
                message=_format_schema_error(error),
            )
        )

    return diagnostics


def _find_error_position(text: str, error) -> tuple[int, int]:
    """Try to find the line/column for a JSON Schema validation error.

    Uses the error's JSON path to locate the offending field in the YAML text.
    Falls back to line 0, col 0 if the position can't be determined.
    """
    if not error.absolute_path:
        return 0, 0

    # Build a search pattern from the path
    # e.g., path ["requirements", 0, "significance"] → look for "significance:" in text
    parts = list(error.absolute_path)
    if parts:
        last = parts[-1]
        if isinstance(last, str):
            # Search for the field name in the YAML text
            pattern = re.compile(r"^\s*(?:-\s+)?" + re.escape(last) + r"\s*:", re.MULTILINE)
            # If there are array indices in the path, try to narrow down
            matches = list(pattern.finditer(text))
            if len(matches) == 1:
                line = text[:matches[0].start()].count("\n")
                col = matches[0].start() - text[:matches[0].start()].rfind("\n") - 1
                return line, col
            elif len(matches) > 1:
                # Use the array index to pick the right match
                array_idx = None
                for p in parts:
                    if isinstance(p, int):
                        array_idx = p
                if array_idx is not None and array_idx < len(matches):
                    m = matches[array_idx]
                    line = text[:m.start()].count("\n")
                    col = m.start() - text[:m.start()].rfind("\n") - 1
                    return line, col
                # Fall back to first match
                m = matches[0]
                line = text[:m.start()].count("\n")
                col = m.start() - text[:m.start()].rfind("\n") - 1
                return line, col

    return 0, 0


def _format_schema_error(error) -> str:
    """Format a jsonschema ValidationError into a user-friendly message."""
    path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
    return f"Schema error at '{path}': {error.message}"
