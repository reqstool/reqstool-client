# Copyright © LFV


import os
from urllib.parse import unquote, urlparse

from lsprotocol import types

from reqstool.lsp.project_state import ProjectState
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData

REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
}


def handle_document_symbols(
    uri: str,
    text: str,
    project: ProjectState | None,
) -> list[types.DocumentSymbol]:
    basename = os.path.basename(uri)
    if basename not in REQSTOOL_YAML_FILES:
        return []
    if project is None or not project.ready:
        return []

    file_path = _uri_to_path(uri)
    line_count = max(1, len(text.splitlines()))

    if basename == "requirements.yml":
        return _symbols_for_requirements(project.get_requirements_for_yaml(file_path), project, line_count)
    if basename == "software_verification_cases.yml":
        return _symbols_for_svcs(project.get_svcs_for_yaml(file_path), project, line_count)
    if basename == "manual_verification_results.yml":
        return _symbols_for_mvrs(project.get_mvrs_for_yaml(file_path), line_count)
    return []


def _symbols_for_requirements(
    reqs: list[RequirementData],
    project: ProjectState,
    line_count: int,
) -> list[types.DocumentSymbol]:
    sorted_reqs = sorted(reqs, key=_source_line_or_inf)
    symbols: list[types.DocumentSymbol] = []
    for idx, req in enumerate(sorted_reqs):
        start = req.source_line if req.source_line is not None else 0
        end = _end_line(sorted_reqs, idx, line_count)
        sel = _selection_range(req, start)
        name = f"{req.id.id} — {req.title}" if req.title else req.id.id
        children = []
        for svc in project.get_svcs_for_req(req.id.id):
            children.append(
                types.DocumentSymbol(
                    name=f"→ {svc.id.id} — {svc.title}",
                    kind=types.SymbolKind.Key,
                    range=_range(start, end),
                    selection_range=sel,
                    detail=svc.verification.value,
                )
            )
        symbols.append(
            types.DocumentSymbol(
                name=name,
                kind=types.SymbolKind.Key,
                range=_range(start, end),
                selection_range=sel,
                detail=req.significance.value,
                children=children if children else None,
            )
        )
    return symbols


def _symbols_for_svcs(
    svcs: list[SVCData],
    project: ProjectState,
    line_count: int,
) -> list[types.DocumentSymbol]:
    sorted_svcs = sorted(svcs, key=_source_line_or_inf)
    symbols: list[types.DocumentSymbol] = []
    for idx, svc in enumerate(sorted_svcs):
        start = svc.source_line if svc.source_line is not None else 0
        end = _end_line(sorted_svcs, idx, line_count)
        sel = _selection_range(svc, start)
        name = f"{svc.id.id} — {svc.title}" if svc.title else svc.id.id
        children = []
        for req_urn_id in svc.requirement_ids:
            children.append(
                types.DocumentSymbol(
                    name=f"← {req_urn_id.id}",
                    kind=types.SymbolKind.Key,
                    range=_range(start, end),
                    selection_range=sel,
                )
            )
        for mvr in project.get_mvrs_for_svc(svc.id.id):
            result = "pass" if mvr.passed else "fail"
            children.append(
                types.DocumentSymbol(
                    name=f"→ MVR: {result}",
                    kind=types.SymbolKind.Key,
                    range=_range(start, end),
                    selection_range=sel,
                )
            )
        symbols.append(
            types.DocumentSymbol(
                name=name,
                kind=types.SymbolKind.Key,
                range=_range(start, end),
                selection_range=sel,
                detail=svc.verification.value,
                children=children if children else None,
            )
        )
    return symbols


def _symbols_for_mvrs(
    mvrs: list[MVRData],
    line_count: int,
) -> list[types.DocumentSymbol]:
    sorted_mvrs = sorted(mvrs, key=_source_line_or_inf)
    symbols: list[types.DocumentSymbol] = []
    for idx, mvr in enumerate(sorted_mvrs):
        start = mvr.source_line if mvr.source_line is not None else 0
        end = _end_line(sorted_mvrs, idx, line_count)
        sel = _selection_range(mvr, start)
        result = "pass" if mvr.passed else "fail"
        name = f"{mvr.id.id} — {result}"
        symbols.append(
            types.DocumentSymbol(
                name=name,
                kind=types.SymbolKind.Key,
                range=_range(start, end),
                selection_range=sel,
                detail="",
            )
        )
    return symbols


def _source_line_or_inf(item) -> float:
    return item.source_line if item.source_line is not None else float("inf")


def _end_line(items, idx: int, line_count: int) -> int:
    if idx + 1 < len(items):
        next_line = items[idx + 1].source_line
        if next_line is not None:
            return max(0, next_line - 1)
    return max(0, line_count - 1)


def _range(start_line: int, end_line: int) -> types.Range:
    return types.Range(
        start=types.Position(line=start_line, character=0),
        end=types.Position(line=end_line, character=0),
    )


def _selection_range(item, fallback_line: int) -> types.Range:
    """Range covering the `id:` value, used by VS Code as the symbol's clickable name.

    VS Code drops symbols whose selection_range is zero-width, so fall back to a
    1-character span at column 0 if the id span wasn't captured.
    """
    if item.source_col_start is not None and item.source_col_end is not None:
        line = item.source_line if item.source_line is not None else fallback_line
        return types.Range(
            start=types.Position(line=line, character=item.source_col_start),
            end=types.Position(line=line, character=item.source_col_end),
        )
    return types.Range(
        start=types.Position(line=fallback_line, character=0),
        end=types.Position(line=fallback_line, character=1),
    )


def _uri_to_path(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return uri
