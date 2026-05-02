# Copyright © LFV


import os
import re
from pathlib import Path

from lsprotocol import types


def handle_workspace_symbols(
    query: str,
    workspace_manager,
) -> list[types.WorkspaceSymbol]:
    results: list[types.WorkspaceSymbol] = []
    query_lower = query.lower()

    for project in workspace_manager.all_projects():
        if not project.ready:
            continue
        initial_urn = project.get_initial_urn() or ""
        _collect_requirements(results, project, initial_urn, query_lower)
        _collect_svcs(results, project, initial_urn, query_lower)
        _collect_mvrs(results, project, initial_urn, query_lower)

    return results


def _collect_requirements(results, project, initial_urn, query_lower):
    for req_id in project.get_all_requirement_ids():
        req = project.get_requirement(req_id)
        if req is None:
            continue
        if query_lower and query_lower not in req_id.lower() and query_lower not in req.title.lower():
            continue
        yaml_path = project.get_yaml_path(req.id.urn or initial_urn, "requirements")
        results.append(types.WorkspaceSymbol(
            name=f"{req.id} — {req.title}",
            kind=types.SymbolKind.Key,
            location=_make_location(yaml_path, req_id),
            data={"id": str(req.id), "type": "requirement"},
        ))


def _collect_svcs(results, project, initial_urn, query_lower):
    for svc_id in project.get_all_svc_ids():
        svc = project.get_svc(svc_id)
        if svc is None:
            continue
        if query_lower and query_lower not in svc_id.lower() and query_lower not in svc.title.lower():
            continue
        yaml_path = project.get_yaml_path(svc.id.urn or initial_urn, "svcs")
        results.append(types.WorkspaceSymbol(
            name=f"{svc.id} — {svc.title}",
            kind=types.SymbolKind.Key,
            location=_make_location(yaml_path, svc_id),
            data={"id": str(svc.id), "type": "svc"},
        ))


def _collect_mvrs(results, project, initial_urn, query_lower):
    for mvr_id in project.get_all_mvr_ids():
        mvr = project.get_mvr(mvr_id)
        if mvr is None:
            continue
        status = "passed" if mvr.passed else "failed"
        if query_lower and query_lower not in mvr_id.lower() and query_lower not in status:
            continue
        yaml_path = project.get_yaml_path(mvr.id.urn or initial_urn, "mvrs")
        results.append(types.WorkspaceSymbol(
            name=f"{mvr.id} — {status}",
            kind=types.SymbolKind.Key,
            location=_make_location(yaml_path, mvr_id),
            data={"id": str(mvr.id), "type": "mvr"},
        ))


def _make_location(yaml_path: str | None, bare_id: str) -> types.Location:
    if yaml_path and os.path.isfile(yaml_path):
        line = _find_id_line(yaml_path, bare_id)
        uri = Path(yaml_path).as_uri()
        return types.Location(
            uri=uri,
            range=types.Range(
                start=types.Position(line=line, character=0),
                end=types.Position(line=line, character=len(bare_id) + 4),
            ),
        )
    return types.Location(
        uri="",
        range=types.Range(
            start=types.Position(line=0, character=0),
            end=types.Position(line=0, character=0),
        ),
    )


def _find_id_line(path: str, bare_id: str) -> int:
    pattern = re.compile(r"^\s*-?\s*id:\s*" + re.escape(bare_id) + r"\s*$")
    try:
        with open(path, encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if pattern.match(line):
                    return idx
    except OSError:
        pass
    return 0
