# Copyright © LFV


import os
import re

from lsprotocol import types

from reqstool.lsp.project_state import ProjectState

# YAML files that the LSP provides document symbols for
REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
}


class _YamlItem:
    """A parsed YAML list item with its fields and line range."""

    __slots__ = ("fields", "start_line", "end_line", "id_line")

    def __init__(self, start_line: int):
        self.fields: dict[str, str] = {}
        self.start_line = start_line
        self.end_line = start_line
        self.id_line = start_line

    @property
    def range(self) -> types.Range:
        return types.Range(
            start=types.Position(line=self.start_line, character=0),
            end=types.Position(line=self.end_line, character=0),
        )

    @property
    def selection_range(self) -> types.Range:
        return types.Range(
            start=types.Position(line=self.id_line, character=0),
            end=types.Position(line=self.id_line, character=0),
        )


def handle_document_symbols(
    uri: str,
    text: str,
    project: ProjectState | None,
) -> list[types.DocumentSymbol]:
    basename = os.path.basename(uri)
    if basename not in REQSTOOL_YAML_FILES:
        return []

    items = _parse_yaml_items(text)
    if not items:
        return []

    if basename == "requirements.yml":
        return _symbols_for_requirements(items, text, project)
    elif basename == "software_verification_cases.yml":
        return _symbols_for_svcs(items, text, project)
    elif basename == "manual_verification_results.yml":
        return _symbols_for_mvrs(items, text, project)

    return []


def _symbols_for_requirements(
    items: list[_YamlItem],
    text: str,
    project: ProjectState | None,
) -> list[types.DocumentSymbol]:
    symbols: list[types.DocumentSymbol] = []
    for item in items:
        req_id = item.fields.get("id", "")
        title = item.fields.get("title", "")
        significance = item.fields.get("significance", "")

        name = f"{req_id} — {title}" if title else req_id
        detail = significance

        children: list[types.DocumentSymbol] = []
        if project is not None and project.ready and req_id:
            svcs = project.get_svcs_for_req(req_id)
            for svc in svcs:
                children.append(
                    types.DocumentSymbol(
                        name=f"→ {svc.id.id} — {svc.title}",
                        kind=types.SymbolKind.Key,
                        range=item.range,
                        selection_range=item.range,
                        detail=svc.verification.value if hasattr(svc, "verification") else "",
                    )
                )

        symbols.append(
            types.DocumentSymbol(
                name=name,
                kind=types.SymbolKind.Key,
                range=item.range,
                selection_range=item.selection_range,
                detail=detail,
                children=children if children else None,
            )
        )

    return symbols


def _symbols_for_svcs(
    items: list[_YamlItem],
    text: str,
    project: ProjectState | None,
) -> list[types.DocumentSymbol]:
    symbols: list[types.DocumentSymbol] = []
    for item in items:
        svc_id = item.fields.get("id", "")
        title = item.fields.get("title", "")
        verification = item.fields.get("verification", "")

        name = f"{svc_id} — {title}" if title else svc_id
        detail = verification

        children: list[types.DocumentSymbol] = []
        if project is not None and project.ready and svc_id:
            svc = project.get_svc(svc_id)
            if svc and svc.requirement_ids:
                for req_ref in svc.requirement_ids:
                    req_id_str = req_ref.id if hasattr(req_ref, "id") else str(req_ref)
                    children.append(
                        types.DocumentSymbol(
                            name=f"← {req_id_str}",
                            kind=types.SymbolKind.Key,
                            range=item.range,
                            selection_range=item.range,
                        )
                    )

            mvrs = project.get_mvrs_for_svc(svc_id)
            for mvr in mvrs:
                result = "pass" if mvr.passed else "fail"
                children.append(
                    types.DocumentSymbol(
                        name=f"→ MVR: {result}",
                        kind=types.SymbolKind.Key,
                        range=item.range,
                        selection_range=item.range,
                    )
                )

        symbols.append(
            types.DocumentSymbol(
                name=name,
                kind=types.SymbolKind.Key,
                range=item.range,
                selection_range=item.selection_range,
                detail=detail,
                children=children if children else None,
            )
        )

    return symbols


def _symbols_for_mvrs(
    items: list[_YamlItem],
    text: str,
    project: ProjectState | None,
) -> list[types.DocumentSymbol]:
    symbols: list[types.DocumentSymbol] = []
    for item in items:
        svc_id = item.fields.get("id", "")
        passed = item.fields.get("passed", "")

        result = "pass" if passed.lower() == "true" else "fail" if passed else ""
        name = f"{svc_id} — {result}" if result else svc_id

        symbols.append(
            types.DocumentSymbol(
                name=name,
                kind=types.SymbolKind.Key,
                range=item.range,
                selection_range=item.selection_range,
                detail="",
            )
        )

    return symbols


def _parse_yaml_items(text: str) -> list[_YamlItem]:
    """Parse YAML text to extract list items under the main collection key.

    Looks for the first top-level array (e.g., requirements:, svcs:, results:)
    and extracts each `- key: value` block.
    """
    lines = text.splitlines()
    items: list[_YamlItem] = []
    current_item: _YamlItem | None = None
    list_indent = -1

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        current_item, list_indent = _process_yaml_line(line, i, items, current_item, list_indent)

    if current_item is not None:
        current_item.end_line = len(lines) - 1
        items.append(current_item)

    return items


def _process_yaml_line(line, i, items, current_item, list_indent):
    """Process a single YAML line, returning updated (current_item, list_indent)."""
    dash_match = re.match(r"^(\s*)-\s+(\w[\w-]*)\s*:\s*(.*)", line)
    if dash_match:
        indent = len(dash_match.group(1))
        if list_indent < 0:
            list_indent = indent
        if indent == list_indent:
            if current_item is not None:
                current_item.end_line = i - 1
                items.append(current_item)
            current_item = _YamlItem(start_line=i)
            current_item.fields[dash_match.group(2)] = dash_match.group(3).strip()
            if dash_match.group(2) == "id":
                current_item.id_line = i
            return current_item, list_indent

    if current_item is not None and list_indent >= 0:
        field_match = re.match(r"^(\s+)(\w[\w-]*)\s*:\s*(.*)", line)
        if field_match and len(field_match.group(1)) > list_indent:
            current_item.fields[field_match.group(2)] = field_match.group(3).strip()
            if field_match.group(2) == "id":
                current_item.id_line = i
            current_item.end_line = i
        elif field_match:
            current_item.end_line = i - 1
            items.append(current_item)
            return None, -1

    return current_item, list_indent
