# Copyright © LFV


import json
import os
import re
import urllib.parse

from lsprotocol import types

from reqstool.lsp.annotation_parser import annotation_at_position
from reqstool.lsp.project_state import ProjectState
from reqstool.lsp.yaml_schema import get_field_description, schema_for_yaml_file

# YAML files that the LSP provides hover for
REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
    "reqstool_config.yml",
}


def handle_hover(
    uri: str,
    position: types.Position,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> types.Hover | None:
    basename = os.path.basename(uri)
    if basename in REQSTOOL_YAML_FILES:
        return _hover_yaml(text, position, basename)
    else:
        return _hover_source(uri, text, position, language_id, project)


def _hover_source(
    uri: str,
    text: str,
    position: types.Position,
    language_id: str,
    project: ProjectState | None,
) -> types.Hover | None:
    match = annotation_at_position(text, position.line, position.character, language_id)
    if match is None:
        return None

    if project is None or not project.ready:
        return types.Hover(
            contents=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"`{match.raw_id}` — *project not loaded*",
            ),
            range=types.Range(
                start=types.Position(line=match.line, character=match.start_col),
                end=types.Position(line=match.line, character=match.end_col),
            ),
        )

    if match.kind == "Requirements":
        return _hover_requirement(match.raw_id, match, project)
    elif match.kind == "SVCs":
        return _hover_svc(match.raw_id, match, project)

    return None


def _open_details_link(raw_id: str, kind: str) -> str:
    args = urllib.parse.quote(json.dumps([{"id": raw_id, "type": kind}]))
    return f"[Open Details](command:reqstool.openDetails?{args})"


def _hover_requirement(raw_id: str, match, project: ProjectState) -> types.Hover | None:
    req = project.get_requirement(raw_id)
    if req is None:
        md = f"**Unknown requirement**: `{raw_id}`"
    else:
        svcs = project.get_svcs_for_req(raw_id)
        svc_ids = ", ".join(f"`{s.id.id}`" for s in svcs) if svcs else "—"
        categories = ", ".join(c.value for c in req.categories) if req.categories else "—"
        impl_count = len(project.get_impl_annotations_for_req(raw_id))

        parts = [
            _open_details_link(raw_id, "requirement"),
            f"### {req.title}",
            f"`{req.id.id}` `{req.significance.value}` `{req.revision}`",
            "---",
            req.description,
        ]
        if req.rationale:
            parts.extend(["---", req.rationale])
        parts.extend(
            [
                "---",
                f"**Categories**: {categories}",
                f"**Lifecycle**: {req.lifecycle.state.value}",
                f"**SVCs**: {svc_ids}",
                f"**Implementations**: {impl_count}",
            ]
        )
        md = "\n\n".join(parts)

    return types.Hover(
        contents=types.MarkupContent(kind=types.MarkupKind.Markdown, value=md),
        range=types.Range(
            start=types.Position(line=match.line, character=match.start_col),
            end=types.Position(line=match.line, character=match.end_col),
        ),
    )


def _hover_svc(raw_id: str, match, project: ProjectState) -> types.Hover | None:
    svc = project.get_svc(raw_id)
    if svc is None:
        md = f"**Unknown SVC**: `{raw_id}`"
    else:
        mvrs = project.get_mvrs_for_svc(raw_id)
        test_results = project.get_test_results_for_svc(raw_id)
        req_ids = ", ".join(f"`{r.id}`" for r in svc.requirement_ids) if svc.requirement_ids else "—"

        test_passed = sum(1 for t in test_results if t.status.value == "passed")
        test_failed = sum(1 for t in test_results if t.status.value == "failed")
        test_missing = sum(1 for t in test_results if t.status.value == "missing")
        mvr_passed = sum(1 for m in mvrs if m.passed)
        mvr_failed = sum(1 for m in mvrs if not m.passed)

        parts = [
            _open_details_link(raw_id, "svc"),
            f"### {svc.title}",
            f"`{svc.id.id}` `{svc.verification.value}` `{svc.revision}`",
            "---",
        ]
        if svc.description:
            parts.append(svc.description)
            parts.append("---")
        if svc.instructions:
            parts.append(svc.instructions)
            parts.append("---")
        parts.extend(
            [
                f"**Lifecycle**: {svc.lifecycle.state.value}",
                f"**Requirements**: {req_ids}",
                f"**Tests**: {test_passed} passed · {test_failed} failed · {test_missing} missing",
                f"**MVRs**: {mvr_passed} passed · {mvr_failed} failed",
            ]
        )
        md = "\n\n".join(parts)

    return types.Hover(
        contents=types.MarkupContent(kind=types.MarkupKind.Markdown, value=md),
        range=types.Range(
            start=types.Position(line=match.line, character=match.start_col),
            end=types.Position(line=match.line, character=match.end_col),
        ),
    )


def _hover_yaml(text: str, position: types.Position, filename: str) -> types.Hover | None:
    """Show JSON Schema description when hovering over a YAML field name."""
    schema = schema_for_yaml_file(filename)
    if schema is None:
        return None

    line = text.splitlines()[position.line] if position.line < len(text.splitlines()) else ""
    field_path = _yaml_field_path_at_line(text, position.line)
    if not field_path:
        return None

    description = get_field_description(schema, field_path)
    if not description:
        return None

    # Find the field name on the current line for hover range
    field_name = field_path[-1]
    field_match = re.search(r"\b" + re.escape(field_name) + r"\s*:", line)
    if field_match:
        start_col = field_match.start()
        end_col = field_match.start() + len(field_name)
    else:
        start_col = 0
        end_col = len(line.rstrip())

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value=f"**{field_name}**: {description}",
        ),
        range=types.Range(
            start=types.Position(line=position.line, character=start_col),
            end=types.Position(line=position.line, character=end_col),
        ),
    )


def _yaml_field_path_at_line(text: str, target_line: int) -> list[str]:
    """Determine the YAML field path at a given line by tracking indentation.

    Handles YAML array items: `  - id: REQ_001` and `    significance: shall`
    both have parent `requirements:` (which is the array container).
    """
    lines = text.splitlines()
    if target_line >= len(lines):
        return []

    target = lines[target_line]
    # Extract field name from "  key: value" or "  key:" or "  - key: value"
    m = re.match(r"^(\s*)(?:-\s+)?(\w[\w-]*)\s*:", target)
    if not m:
        return []

    leading_spaces = len(m.group(1))
    field_name = m.group(2)

    path = [field_name]

    # Walk backwards to find parent fields with less indentation.
    # Skip lines that are list item entries (have "- " prefix) — they are
    # siblings within the same array, not structural parents.
    current_indent = leading_spaces
    for i in range(target_line - 1, -1, -1):
        line = lines[i]
        pm = re.match(r"^(\s*)(-\s+)?(\w[\w-]*)\s*:", line)
        if pm:
            indent = len(pm.group(1))
            has_dash = pm.group(2) is not None
            if indent < current_indent and not has_dash:
                path.insert(0, pm.group(3))
                current_indent = indent
                if indent == 0:
                    break

    return path
