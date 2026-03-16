# Copyright © LFV

from __future__ import annotations

import logging
import os
import re

from lsprotocol import types

from reqstool.lsp.annotation_parser import annotation_at_position
from reqstool.lsp.project_state import ProjectState

logger = logging.getLogger(__name__)

# YAML files where IDs can be defined
YAML_ID_FILES = {
    "requirements.yml": "requirements",
    "software_verification_cases.yml": "svcs",
    "manual_verification_results.yml": "mvrs",
}


def handle_definition(
    uri: str,
    position: types.Position,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> list[types.Location]:
    basename = os.path.basename(uri)
    if basename in YAML_ID_FILES:
        return _definition_from_yaml(text, position, basename, project)
    else:
        return _definition_from_source(text, position, language_id, project)


def _definition_from_source(
    text: str,
    position: types.Position,
    language_id: str,
    project: ProjectState | None,
) -> list[types.Location]:
    """Go-to-definition from @Requirements/@SVCs annotation → YAML file."""
    if project is None or not project.ready:
        return []

    match = annotation_at_position(text, position.line, position.character, language_id)
    if match is None:
        return []

    initial_urn = project.get_initial_urn()
    if not initial_urn:
        return []

    if match.kind == "Requirements":
        yaml_file = project.get_yaml_path(initial_urn, "requirements")
    elif match.kind == "SVCs":
        yaml_file = project.get_yaml_path(initial_urn, "svcs")
    else:
        return []

    if yaml_file is None:
        return []

    return _find_id_in_yaml(yaml_file, match.raw_id)


def _definition_from_yaml(
    text: str,
    position: types.Position,
    filename: str,
    project: ProjectState | None,
) -> list[types.Location]:
    """Go-to-definition from YAML ID → source file annotations."""
    raw_id = _id_at_yaml_position(text, position)
    if raw_id is None:
        return []

    if project is None or not project.ready:
        return []

    initial_urn = project.get_initial_urn()
    if not initial_urn:
        return []

    # Determine what kind of ID this is based on the YAML file
    file_kind = YAML_ID_FILES.get(filename)

    if file_kind == "requirements":
        # From requirement ID → find references in SVC file (e.g. requirement_ids: ["REQ_PASS"])
        svc_file = project.get_yaml_path(initial_urn, "svcs")
        if svc_file is None:
            return []
        return _find_reference_in_yaml(svc_file, raw_id)
    elif file_kind == "svcs":
        # From SVC ID → find references in MVR file (e.g. svc_ids: ["SVC_021"])
        mvr_file = project.get_yaml_path(initial_urn, "mvrs")
        if mvr_file is None:
            return []
        return _find_reference_in_yaml(mvr_file, raw_id)

    return []


def _find_id_in_yaml(yaml_file: str, raw_id: str) -> list[types.Location]:
    """Search a YAML file for a line containing `id: <raw_id>` and return its location."""
    if not os.path.isfile(yaml_file):
        return []

    try:
        with open(yaml_file) as f:
            lines = f.readlines()
    except OSError:
        return []

    pattern = re.compile(r"^\s*(?:-\s+)?id\s*:\s*" + re.escape(raw_id) + r"\s*$")
    uri = _path_to_uri(yaml_file)

    locations: list[types.Location] = []
    for i, line in enumerate(lines):
        if pattern.match(line):
            locations.append(
                types.Location(
                    uri=uri,
                    range=types.Range(
                        start=types.Position(line=i, character=0),
                        end=types.Position(line=i, character=len(line.rstrip())),
                    ),
                )
            )

    return locations


def _find_reference_in_yaml(yaml_file: str, raw_id: str) -> list[types.Location]:
    """Search a YAML file for any line containing the given ID (word-boundary match)."""
    if not os.path.isfile(yaml_file):
        return []

    try:
        with open(yaml_file) as f:
            lines = f.readlines()
    except OSError:
        return []

    pattern = re.compile(r"\b" + re.escape(raw_id) + r"\b")
    uri = _path_to_uri(yaml_file)

    locations: list[types.Location] = []
    for i, line in enumerate(lines):
        if pattern.search(line):
            locations.append(
                types.Location(
                    uri=uri,
                    range=types.Range(
                        start=types.Position(line=i, character=0),
                        end=types.Position(line=i, character=len(line.rstrip())),
                    ),
                )
            )

    return locations


def _id_at_yaml_position(text: str, position: types.Position) -> str | None:
    """Extract the requirement/SVC ID at the cursor position in a YAML file.

    Looks for patterns like `id: REQ_001` or `- id: REQ_001` on the current line,
    and also for ID references in other fields (e.g. requirement_ids entries).
    """
    lines = text.splitlines()
    if position.line >= len(lines):
        return None

    line = lines[position.line]

    # Match `id: VALUE` or `- id: VALUE`
    m = re.match(r"^\s*(?:-\s+)?id\s*:\s*(\S+)", line)
    if m:
        return m.group(1)

    # Match bare ID in a list (e.g., `    - REQ_001`)
    m = re.match(r"^\s*-\s+(\w[\w:-]*)\s*$", line)
    if m:
        return m.group(1)

    return None


def _path_to_uri(path: str) -> str:
    """Convert a file path to a file URI."""
    abs_path = os.path.abspath(path)
    return "file://" + abs_path
