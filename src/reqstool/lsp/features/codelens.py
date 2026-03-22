# Copyright © LFV

from __future__ import annotations

from lsprotocol import types

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.lsp.annotation_parser import find_all_annotations
from reqstool.lsp.project_state import ProjectState


def handle_code_lens(
    uri: str,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> list[types.CodeLens]:
    if project is None or not project.ready:
        return []

    annotations = find_all_annotations(text, language_id)
    if not annotations:
        return []

    # Group annotation matches by (line, kind)
    by_line: dict[tuple[int, str], list[str]] = {}
    for match in annotations:
        key = (match.line, match.kind)
        by_line.setdefault(key, []).append(match.raw_id)

    lines = text.splitlines()
    result: list[types.CodeLens] = []

    for (line_idx, kind), ids in by_line.items():
        line_len = len(lines[line_idx]) if line_idx < len(lines) else 0
        lens_range = types.Range(
            start=types.Position(line=line_idx, character=0),
            end=types.Position(line=line_idx, character=line_len),
        )

        if kind == "Requirements":
            label = _req_label(ids, project)
            item_type = "requirement"
        else:
            label = _svc_label(ids, project)
            item_type = "svc"

        result.append(
            types.CodeLens(
                range=lens_range,
                command=types.Command(
                    title=label,
                    command="reqstool.openDetails",
                    arguments=[{"ids": ids, "type": item_type}],
                ),
            )
        )

    return result


def _lifecycle_badge(state: LIFECYCLESTATE) -> str:
    if state == LIFECYCLESTATE.DEPRECATED:
        return "⚠ "
    if state == LIFECYCLESTATE.OBSOLETE:
        return "✕ "
    return ""


def _req_label(ids: list[str], project: ProjectState) -> str:
    all_svcs = []
    for raw_id in ids:
        all_svcs.extend(project.get_svcs_for_req(raw_id))

    pass_count = 0
    fail_count = 0
    for svc in all_svcs:
        for mvr in project.get_mvrs_for_svc(svc.id.id):
            if mvr.passed:
                pass_count += 1
            else:
                fail_count += 1

    id_parts = []
    for raw_id in ids:
        req = project.get_requirement(raw_id)
        badge = _lifecycle_badge(req.lifecycle.state) if req else ""
        id_parts.append(f"{badge}{raw_id}")
    id_str = ", ".join(id_parts)
    svc_count = len(all_svcs)

    if pass_count == 0 and fail_count == 0:
        return f"{id_str}: {svc_count} SVCs"
    return f"{id_str}: {svc_count} SVCs · {pass_count}✓ {fail_count}✗"


def _svc_label(ids: list[str], project: ProjectState) -> str:
    id_parts = []
    for raw_id in ids:
        svc = project.get_svc(raw_id)
        badge = _lifecycle_badge(svc.lifecycle.state) if svc else ""
        id_parts.append(f"{badge}{raw_id}")
    id_str = ", ".join(id_parts)

    if len(ids) == 1:
        svc = project.get_svc(ids[0])
        if svc is not None:
            mvrs = project.get_mvrs_for_svc(ids[0])
            if mvrs:
                result = "pass" if all(m.passed for m in mvrs) else "fail"
                return f"{id_str}: {svc.verification.value} · {result}"
            return f"{id_str}: {svc.verification.value}"
    return id_str
