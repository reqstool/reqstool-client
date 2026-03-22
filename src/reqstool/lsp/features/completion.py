# Copyright © LFV

from __future__ import annotations

import os
import re

from lsprotocol import types

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.lsp.annotation_parser import is_inside_annotation
from reqstool.lsp.project_state import ProjectState
from reqstool.lsp.yaml_schema import get_enum_values, schema_for_yaml_file

# YAML files that the LSP provides completion for
REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
    "reqstool_config.yml",
}


def handle_completion(
    uri: str,
    position: types.Position,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> types.CompletionList | None:
    basename = os.path.basename(uri)
    if basename in REQSTOOL_YAML_FILES:
        return _complete_yaml(text, position, basename)
    else:
        return _complete_source(text, position, language_id, project)


def _complete_source(
    text: str,
    position: types.Position,
    language_id: str,
    project: ProjectState | None,
) -> types.CompletionList | None:
    if project is None or not project.ready:
        return None

    lines = text.splitlines()
    if position.line >= len(lines):
        return None
    line_text = lines[position.line]

    kind = is_inside_annotation(line_text, position.character, language_id)
    if kind is None:
        return None

    items: list[types.CompletionItem] = []

    if kind == "Requirements":
        items = _req_completions(project)
    elif kind == "SVCs":
        items = _svc_completions(project)

    if not items:
        return None

    return types.CompletionList(is_incomplete=False, items=items)


_INACTIVE = (LIFECYCLESTATE.DEPRECATED, LIFECYCLESTATE.OBSOLETE)


def _req_completions(project: ProjectState) -> list[types.CompletionItem]:
    items = []
    for req_id in project.get_all_requirement_ids():
        req = project.get_requirement(req_id)
        if req is not None and req.lifecycle.state in _INACTIVE:
            continue
        items.append(
            types.CompletionItem(
                label=req_id,
                kind=types.CompletionItemKind.Reference,
                detail=req.title if req else "",
                documentation=req.description if req else "",
            )
        )
    return items


def _svc_completions(project: ProjectState) -> list[types.CompletionItem]:
    items = []
    for svc_id in project.get_all_svc_ids():
        svc = project.get_svc(svc_id)
        if svc is not None and svc.lifecycle.state in _INACTIVE:
            continue
        doc = svc.description if svc else ""
        items.append(
            types.CompletionItem(
                label=svc_id,
                kind=types.CompletionItemKind.Reference,
                detail=svc.title if svc else "",
                documentation=doc if doc else None,
            )
        )
    return items


def _complete_yaml(
    text: str,
    position: types.Position,
    filename: str,
) -> types.CompletionList | None:
    schema = schema_for_yaml_file(filename)
    if schema is None:
        return None

    lines = text.splitlines()
    if position.line >= len(lines):
        return None

    field_path = _yaml_value_context(text, position.line)
    if not field_path:
        return None

    values = get_enum_values(schema, field_path)
    if not values:
        return None

    items = [
        types.CompletionItem(
            label=v,
            kind=types.CompletionItemKind.EnumMember,
        )
        for v in values
    ]

    return types.CompletionList(is_incomplete=False, items=items)


def _yaml_value_context(text: str, target_line: int) -> list[str] | None:
    """Determine the field path for the value being typed at target_line.

    Returns the field path if the cursor is in the value position of a YAML field,
    or None if not on a field line.
    """
    lines = text.splitlines()
    if target_line >= len(lines):
        return None

    target = lines[target_line]
    m = re.match(r"^(\s*)(?:-\s+)?(\w[\w-]*)\s*:", target)
    if not m:
        return None

    leading_spaces = len(m.group(1))
    field_name = m.group(2)
    path = [field_name]

    # Walk backwards for parent fields (same logic as hover's _yaml_field_path_at_line)
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
