# Copyright © LFV


import logging
import os
import re

from lsprotocol import types

from reqstool.lsp.annotation_parser import annotation_at_position, find_all_annotations
from reqstool.lsp.project_state import ProjectState

logger = logging.getLogger(__name__)

REQSTOOL_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
}

_ID_LINE_RE = re.compile(r"^\s*(?:-\s+)?id\s*:\s*(\S+)")


def handle_implementation(
    uri: str,
    position: types.Position,
    text: str,
    language_id: str,
    project: ProjectState | None,
    workspace_text_documents: dict,
) -> list[types.Location]:
    """Go to Test: navigate to the SVCs (in YAML) or @SVCs test annotations (in source)
    that verify a given requirement or implement a given SVC."""
    if project is None or not project.ready:
        return []

    basename = os.path.basename(uri)

    if basename == "requirements.yml":
        return _from_yaml_req(text, position, workspace_text_documents)

    if basename == "software_verification_cases.yml":
        return _from_yaml_svc(text, position, workspace_text_documents)

    if basename not in REQSTOOL_YAML_FILES:
        # Source file: @Requirements annotation → source @SVCs test annotations
        match = annotation_at_position(text, position.line, position.character, language_id)
        if match and match.kind == "Requirements":
            return _svcs_in_source_for_req(match.raw_id, project, workspace_text_documents)

    return []


def _from_yaml_req(
    text: str,
    position: types.Position,
    workspace_text_documents: dict,
) -> list[types.Location]:
    """YAML requirements.yml id: REQ → source @Requirements annotations."""
    lines = text.splitlines()
    if position.line >= len(lines):
        return []
    m = _ID_LINE_RE.match(lines[position.line])
    if not m:
        return []
    bare_id = m.group(1).split(":")[-1]
    return _req_annotations_in_source(bare_id, workspace_text_documents)


def _req_annotations_in_source(bare_req_id: str, workspace_text_documents: dict) -> list[types.Location]:
    """Find @Requirements("REQ-001") annotations in open source documents."""
    locations: list[types.Location] = []
    for doc_uri, doc in workspace_text_documents.items():
        if os.path.basename(doc_uri) in REQSTOOL_YAML_FILES:
            continue
        lang = getattr(doc, "language_id", None) or ""
        for ann in find_all_annotations(doc.source, lang):
            if ann.kind == "Requirements" and ann.raw_id.split(":")[-1] == bare_req_id:
                locations.append(
                    types.Location(
                        uri=doc_uri,
                        range=types.Range(
                            start=types.Position(line=ann.line, character=ann.start_col),
                            end=types.Position(line=ann.line, character=ann.end_col),
                        ),
                    )
                )
    return locations


def _from_yaml_svc(
    text: str,
    position: types.Position,
    workspace_text_documents: dict,
) -> list[types.Location]:
    """YAML svcs.yml id: SVC → source @SVCs test annotations in open documents."""
    lines = text.splitlines()
    if position.line >= len(lines):
        return []
    m = _ID_LINE_RE.match(lines[position.line])
    if not m:
        return []
    bare_id = m.group(1).split(":")[-1]
    return _svc_annotations_in_source(bare_id, workspace_text_documents)


def _svcs_in_source_for_req(
    raw_req_id: str,
    project: ProjectState,
    workspace_text_documents: dict,
) -> list[types.Location]:
    """Source @Requirements(REQ) → source @SVCs for all SVCs that verify this requirement."""
    svcs = project.get_svcs_for_req(raw_req_id)
    locations: list[types.Location] = []
    for svc in svcs:
        locations.extend(_svc_annotations_in_source(svc.id.id, workspace_text_documents))
    return locations


def _svc_annotations_in_source(bare_svc_id: str, workspace_text_documents: dict) -> list[types.Location]:
    """Find @SVCs("SVC-001") annotations in open source documents."""
    locations: list[types.Location] = []
    for doc_uri, doc in workspace_text_documents.items():
        if os.path.basename(doc_uri) in REQSTOOL_YAML_FILES:
            continue
        lang = getattr(doc, "language_id", None) or ""
        for ann in find_all_annotations(doc.source, lang):
            if ann.kind == "SVCs" and ann.raw_id.split(":")[-1] == bare_svc_id:
                locations.append(
                    types.Location(
                        uri=doc_uri,
                        range=types.Range(
                            start=types.Position(line=ann.line, character=ann.start_col),
                            end=types.Position(line=ann.line, character=ann.end_col),
                        ),
                    )
                )
    return locations
