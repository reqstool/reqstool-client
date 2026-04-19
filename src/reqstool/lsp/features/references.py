# Copyright © LFV


import os
import re
from pathlib import Path

from lsprotocol import types

from reqstool.lsp.annotation_parser import annotation_at_position, find_all_annotations
from reqstool.lsp.project_state import ProjectState

REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
}

# Matches bare IDs like REQ_010 or SVC_010 as a whole word
_ID_RE_CACHE: dict[str, re.Pattern] = {}


def _id_pattern(raw_id: str) -> re.Pattern:
    bare = raw_id.split(":")[-1]
    if bare not in _ID_RE_CACHE:
        _ID_RE_CACHE[bare] = re.compile(r"\b" + re.escape(bare) + r"\b")
    return _ID_RE_CACHE[bare]


def handle_references(
    uri: str,
    position: types.Position,
    text: str,
    language_id: str,
    project: ProjectState | None,
    include_declaration: bool,
    workspace_text_documents: dict,
) -> list[types.Location]:
    if project is None or not project.ready:
        return []

    raw_id = _resolve_id_at_position(uri, position, text, language_id)
    if not raw_id:
        return []

    pattern = _id_pattern(raw_id)
    locations: list[types.Location] = []
    seen_uris: set[str] = set()

    _search_open_documents(workspace_text_documents, raw_id, pattern, include_declaration, locations, seen_uris)
    _search_project_yaml_files(project, pattern, include_declaration, locations, seen_uris)

    return locations


def _search_open_documents(
    workspace_text_documents: dict,
    raw_id: str,
    pattern: re.Pattern,
    include_declaration: bool,
    locations: list[types.Location],
    seen_uris: set[str],
) -> None:
    bare_search = raw_id.split(":")[-1]
    for doc_uri, doc in workspace_text_documents.items():
        seen_uris.add(doc_uri)
        basename = os.path.basename(doc_uri)
        if basename in REQSTOOL_YAML_FILES:
            _search_yaml_text(doc_uri, doc.source, pattern, include_declaration, locations)
        else:
            lang = getattr(doc, "language_id", None) or ""
            for ann in find_all_annotations(doc.source, lang):
                if ann.raw_id.split(":")[-1] == bare_search:
                    locations.append(
                        types.Location(
                            uri=doc_uri,
                            range=types.Range(
                                start=types.Position(line=ann.line, character=ann.start_col),
                                end=types.Position(line=ann.line, character=ann.end_col),
                            ),
                        )
                    )


def _search_project_yaml_files(
    project: ProjectState,
    pattern: re.Pattern,
    include_declaration: bool,
    locations: list[types.Location],
    seen_uris: set[str],
) -> None:
    for urn_paths in project.get_yaml_paths().values():
        for file_type, path in urn_paths.items():
            if file_type not in ("requirements", "svcs", "mvrs"):
                continue
            if not path or not os.path.isfile(path):
                continue
            file_uri = Path(path).as_uri()
            if file_uri in seen_uris:
                continue
            seen_uris.add(file_uri)
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                _search_yaml_text(file_uri, content, pattern, include_declaration, locations)
            except OSError:
                pass


def _resolve_id_at_position(uri: str, position: types.Position, text: str, language_id: str) -> str | None:
    basename = os.path.basename(uri)
    if basename in REQSTOOL_YAML_FILES:
        lines = text.splitlines()
        if position.line < len(lines):
            m = re.match(r"^\s*-?\s*id:\s*(\S+)", lines[position.line])
            if m:
                return m.group(1)
        return None
    match = annotation_at_position(text, position.line, position.character, language_id)
    return match.raw_id if match else None


def _search_yaml_text(
    file_uri: str,
    content: str,
    pattern: re.Pattern,
    include_declaration: bool,
    locations: list[types.Location],
) -> None:
    for line_idx, line in enumerate(content.splitlines()):
        m = pattern.search(line)
        if not m:
            continue
        is_decl = bool(re.match(r"^\s*-?\s*id:\s*", line))
        if is_decl and not include_declaration:
            continue
        col = m.start()
        locations.append(
            types.Location(
                uri=file_uri,
                range=types.Range(
                    start=types.Position(line=line_idx, character=col),
                    end=types.Position(line=line_idx, character=col + len(m.group(0))),
                ),
            )
        )
