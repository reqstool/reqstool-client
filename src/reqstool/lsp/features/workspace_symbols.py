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

        for req_id in project.get_all_requirement_ids():
            req = project.get_requirement(req_id)
            if req is None:
                continue
            if query_lower and query_lower not in req_id.lower() and query_lower not in req.title.lower():
                continue
            name = f"{req_id} \u2014 {req.title}"
            yaml_path = project.get_yaml_path(req.id.urn or initial_urn, "requirements")
            location = _make_location(yaml_path, req_id)
            results.append(
                types.WorkspaceSymbol(
                    name=name,
                    kind=types.SymbolKind.Key,
                    location=location,
                )
            )

        for svc_id in project.get_all_svc_ids():
            svc = project.get_svc(svc_id)
            if svc is None:
                continue
            if query_lower and query_lower not in svc_id.lower() and query_lower not in svc.title.lower():
                continue
            name = f"{svc_id} \u2014 {svc.title}"
            yaml_path = project.get_yaml_path(svc.id.urn or initial_urn, "svcs")
            location = _make_location(yaml_path, svc_id)
            results.append(
                types.WorkspaceSymbol(
                    name=name,
                    kind=types.SymbolKind.Key,
                    location=location,
                )
            )

    return results


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
