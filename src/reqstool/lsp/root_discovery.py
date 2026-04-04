# Copyright © LFV

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from ruamel.yaml import YAML

from reqstool.models.requirements import VARIANTS

logger = logging.getLogger(__name__)

SKIP_DIRS = {".git", "node_modules", "build", "target", "__pycache__", ".hatch", ".tox", ".venv", "venv"}
MAX_DEPTH = 5


@dataclass(frozen=True)
class DiscoveredProject:
    path: str  # directory containing requirements.yml
    urn: str  # metadata.urn
    variant: VARIANTS  # system/microservice/external
    imported_urns: frozenset[str] = field(default_factory=frozenset)  # URNs referenced in imports
    implemented_urns: frozenset[str] = field(default_factory=frozenset)  # URNs referenced in implementations


def discover_root_projects(workspace_folder: str) -> list[DiscoveredProject]:
    """Find root reqstool projects in a workspace folder.

    1. Glob for **/requirements.yml (max depth, skip build dirs)
    2. Quick-parse each: extract metadata.urn, metadata.variant, imports, implementations
    3. Build local reference graph
    4. Return projects not referenced by any other local project (externals excluded)
    """
    req_files = _find_requirements_files(workspace_folder)
    if not req_files:
        return []

    projects = []
    for req_file in req_files:
        project = _quick_parse(req_file)
        if project is not None:
            projects.append(project)

    if not projects:
        return []

    return _find_roots(projects)


def _find_requirements_files(workspace_folder: str) -> list[str]:
    results = []
    _walk_dir(workspace_folder, 0, results)
    return results


def _walk_dir(dirpath: str, depth: int, results: list[str]) -> None:
    if depth > MAX_DEPTH:
        return
    if os.path.exists(os.path.join(dirpath, ".reqstoolignore")):
        return
    try:
        entries = os.scandir(dirpath)
    except PermissionError:
        return

    subdirs = []
    for entry in entries:
        if entry.is_file() and entry.name == "requirements.yml":
            results.append(dirpath)
        elif entry.is_dir() and not entry.name.startswith(".") and entry.name not in SKIP_DIRS:
            subdirs.append(entry.path)

    for subdir in subdirs:
        _walk_dir(subdir, depth + 1, results)


def _quick_parse(req_dir: str) -> DiscoveredProject | None:
    req_file = os.path.join(req_dir, "requirements.yml")
    yaml = YAML()
    try:
        with open(req_file) as f:
            data = yaml.load(f)
    except Exception as e:
        logger.warning("Failed to parse %s: %s", req_file, e)
        return None

    if not isinstance(data, dict):
        return None

    metadata = data.get("metadata", {})
    urn = metadata.get("urn")
    variant_str = metadata.get("variant")
    if not urn or not variant_str:
        return None

    try:
        variant = VARIANTS(variant_str)
    except ValueError:
        logger.warning("Unknown variant %r in %s", variant_str, req_file)
        return None

    imported_urns = _extract_import_urns(data)
    implemented_urns = _extract_implementation_urns(data)

    return DiscoveredProject(
        path=req_dir,
        urn=urn,
        variant=variant,
        imported_urns=frozenset(imported_urns),
        implemented_urns=frozenset(implemented_urns),
    )


def _extract_import_urns(data: dict) -> set[str]:
    """Extract URNs referenced in the imports section.

    Imports can reference local paths — we resolve these to URNs by quick-parsing
    the imported requirements.yml. For non-local imports (git, maven, pypi),
    we skip them as they are remote.
    """
    urns = set()
    imports = data.get("imports", {})
    if not isinstance(imports, dict):
        return urns

    local_imports = imports.get("local", [])
    if isinstance(local_imports, list):
        for item in local_imports:
            if isinstance(item, dict) and "path" in item:
                urns.add(item["path"])
    return urns


def _extract_implementation_urns(data: dict) -> set[str]:
    """Extract URNs referenced in the implementations section."""
    urns = set()
    implementations = data.get("implementations", {})
    if not isinstance(implementations, dict):
        return urns

    local_impls = implementations.get("local", [])
    if isinstance(local_impls, list):
        for item in local_impls:
            if isinstance(item, dict) and "path" in item:
                urns.add(item["path"])
    return urns


def _find_roots(projects: list[DiscoveredProject]) -> list[DiscoveredProject]:
    """A project is a root if no other local project references it.

    We match by resolving relative paths: if project A imports "../B",
    we check if B's absolute path matches any other project's path.
    External-variant projects are never roots.
    """
    # Build a set of all project paths that are referenced by other projects
    referenced_paths: set[str] = set()
    for project in projects:
        for rel_path in project.imported_urns | project.implemented_urns:
            abs_path = os.path.normpath(os.path.join(project.path, rel_path))
            referenced_paths.add(abs_path)

    roots = []
    for project in projects:
        if project.variant == VARIANTS.EXTERNAL:
            continue
        norm_path = os.path.normpath(project.path)
        if norm_path not in referenced_paths:
            roots.append(project)

    # If no roots found (e.g., circular references), fall back to all non-external projects
    if not roots:
        roots = [p for p in projects if p.variant != VARIANTS.EXTERNAL]

    return roots
