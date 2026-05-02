# Copyright © LFV


from lsprotocol import types

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.lsp.annotation_parser import find_all_annotations
from reqstool.lsp.project_state import ProjectState
from reqstool.lsp.workspace_manager import WorkspaceManager


def handle_code_lens(
    uri: str,
    text: str,
    language_id: str,
    project: ProjectState | None,
    workspace_manager: WorkspaceManager | None = None,
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
            label = _req_label(ids, project, workspace_manager)
            item_type = "requirement"
        else:
            label = _svc_label(ids, project, workspace_manager)
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


def _req_label(ids: list[str], project: ProjectState, workspace_manager: WorkspaceManager | None = None) -> str:
    all_svcs = []
    for raw_id in ids:
        p = workspace_manager.resolve_project(raw_id, project) if workspace_manager else project
        all_svcs.extend(p.get_svcs_for_req(raw_id))

    pass_count = 0
    fail_count = 0
    for svc in all_svcs:
        svc_project = (workspace_manager.project_for_urn(svc.id.urn) or project) if workspace_manager else project
        for mvr in svc_project.get_mvrs_for_svc(str(svc.id)):
            if mvr.passed:
                pass_count += 1
            else:
                fail_count += 1

    svc_count = len(all_svcs)
    counts = (
        f"{svc_count} SVCs"
        if pass_count == 0 and fail_count == 0
        else f"{svc_count} SVCs · {pass_count}✓ {fail_count}✗"
    )

    badges = []
    for raw_id in ids:
        p = workspace_manager.resolve_project(raw_id, project) if workspace_manager else project
        req = p.get_requirement(raw_id)
        badge = _lifecycle_badge(req.lifecycle.state) if req else ""
        badges.append(f"{badge}{raw_id}")
    id_str = ", ".join(badges)
    return f"{id_str}: {counts}"


def _svc_label(ids: list[str], project: ProjectState, workspace_manager: WorkspaceManager | None = None) -> str:
    id_parts = []
    for raw_id in ids:
        p = workspace_manager.resolve_project(raw_id, project) if workspace_manager else project
        svc = p.get_svc(raw_id)
        badge = _lifecycle_badge(svc.lifecycle.state) if svc else ""
        id_parts.append(f"{badge}{raw_id}")
    id_str = ", ".join(id_parts)

    if len(ids) == 1:
        p = workspace_manager.resolve_project(ids[0], project) if workspace_manager else project
        svc = p.get_svc(ids[0])
        if svc is not None:
            svc_project = (workspace_manager.project_for_urn(svc.id.urn) or project) if workspace_manager else project
            mvrs = svc_project.get_mvrs_for_svc(str(svc.id))
            if mvrs:
                result = "pass" if all(m.passed for m in mvrs) else "fail"
                return f"{id_str}: {svc.verification.value} · {result}"
            return f"{id_str}: {svc.verification.value}"
    return id_str
