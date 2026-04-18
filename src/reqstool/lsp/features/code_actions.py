# Copyright © LFV


import re

from lsprotocol import types

from reqstool.lsp.annotation_parser import annotation_at_position
from reqstool.lsp.project_state import ProjectState

# Patterns matching diagnostic messages from diagnostics.py
_UNKNOWN_REQ_RE = re.compile(r"Unknown requirement: (.+)")
_UNKNOWN_SVC_RE = re.compile(r"Unknown SVC: (.+)")
_LIFECYCLE_RE = re.compile(r"(Requirement|SVC) (.+) is (?:deprecated|obsolete)")


def handle_code_actions(
    uri: str,
    range_: types.Range,
    context: types.CodeActionContext,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> list[types.CodeAction]:
    only = set(context.only) if context.only else None
    actions = _actions_from_diagnostics(uri, context.diagnostics, only)
    actions += _source_action(uri, range_, text, language_id, project, only)
    return actions


def _actions_from_diagnostics(
    uri: str,
    diagnostics: list,
    only: set | None,
) -> list[types.CodeAction]:
    actions: list[types.CodeAction] = []
    if only is not None and types.CodeActionKind.QuickFix not in only:
        return actions
    for diag in diagnostics:
        if diag.source != "reqstool":
            continue
        action = _action_from_message(diag.message, uri)
        if action is not None:
            actions.append(action)
    return actions


def _action_from_message(msg: str, uri: str) -> types.CodeAction | None:
    m = _UNKNOWN_REQ_RE.match(msg)
    if m:
        raw_id = m.group(1)
        return _make_action(f"Open Details for {raw_id}", raw_id, uri, "requirement", types.CodeActionKind.QuickFix)
    m = _UNKNOWN_SVC_RE.match(msg)
    if m:
        raw_id = m.group(1)
        return _make_action(f"Open Details for {raw_id}", raw_id, uri, "svc", types.CodeActionKind.QuickFix)
    m = _LIFECYCLE_RE.match(msg)
    if m:
        kind_label, raw_id = m.group(1), m.group(2)
        item_type = "requirement" if kind_label == "Requirement" else "svc"
        return _make_action(f"View details for {raw_id}", raw_id, uri, item_type, types.CodeActionKind.QuickFix)
    return None


def _source_action(
    uri: str,
    range_: types.Range,
    text: str,
    language_id: str,
    project: ProjectState | None,
    only: set | None,
) -> list[types.CodeAction]:
    if project is None or not project.ready:
        return []
    if only is not None and types.CodeActionKind.Source not in only:
        return []
    match = annotation_at_position(text, range_.start.line, range_.start.character, language_id)
    if match is None:
        return []
    item_type = "requirement" if match.kind == "Requirements" else "svc"
    known = project.get_requirement(match.raw_id) if match.kind == "Requirements" else project.get_svc(match.raw_id)
    if known is None:
        return []
    return [_make_action("Open Details", match.raw_id, uri, item_type, types.CodeActionKind.Source)]


def _make_action(
    title: str,
    raw_id: str,
    uri: str,
    item_type: str,
    kind: types.CodeActionKind,
) -> types.CodeAction:
    return types.CodeAction(
        title=title,
        kind=kind,
        command=types.Command(
            title=title,
            command="reqstool.openDetails",
            arguments=[{"id": raw_id, "uri": uri, "type": item_type}],
        ),
    )
