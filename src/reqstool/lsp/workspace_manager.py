# Copyright © LFV

from __future__ import annotations

import logging
import os
from urllib.parse import unquote, urlparse

from reqstool.lsp.project_state import ProjectState
from reqstool.lsp.root_discovery import discover_root_projects

logger = logging.getLogger(__name__)

STATIC_YAML_FILES = {
    "requirements.yml",
    "software_verification_cases.yml",
    "manual_verification_results.yml",
    "reqstool_config.yml",
}


class WorkspaceManager:
    def __init__(self):
        self._folder_projects: dict[str, list[ProjectState]] = {}

    def add_folder(self, folder_uri: str) -> list[ProjectState]:
        folder_path = uri_to_path(folder_uri)
        roots = discover_root_projects(folder_path)

        projects = []
        for root in roots:
            project = ProjectState(reqstool_path=root.path)
            project.build()
            projects.append(project)
            logger.info(
                "Discovered root project: urn=%s variant=%s path=%s ready=%s",
                root.urn,
                root.variant.value,
                root.path,
                project.ready,
            )

        self._folder_projects[folder_uri] = projects
        return projects

    def remove_folder(self, folder_uri: str) -> None:
        projects = self._folder_projects.pop(folder_uri, [])
        for project in projects:
            project.close()

    def rebuild_folder(self, folder_uri: str) -> None:
        for project in self._folder_projects.get(folder_uri, []):
            project.rebuild()

    def rebuild_all(self) -> None:
        for folder_uri in self._folder_projects:
            self.rebuild_folder(folder_uri)

    def rebuild_affected(self, file_uri: str) -> ProjectState | None:
        """Rebuild the project affected by a changed file. Returns the project or None."""
        project = self.project_for_file(file_uri)
        if project is not None:
            project.rebuild()
        return project

    def project_for_file(self, file_uri: str) -> ProjectState | None:
        file_path = uri_to_path(file_uri)
        best_match: ProjectState | None = None
        best_depth = -1

        for projects in self._folder_projects.values():
            for project in projects:
                reqstool_path = os.path.normpath(project.reqstool_path)
                norm_file = os.path.normpath(file_path)
                # Check if the file is within the project's directory tree
                if norm_file.startswith(reqstool_path + os.sep) or norm_file == reqstool_path:
                    depth = reqstool_path.count(os.sep)
                    if depth > best_depth:
                        best_match = project
                        best_depth = depth

        # If no direct match, find the closest project by walking up from the file
        if best_match is None:
            file_dir = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path
            best_match = self._find_closest_project(file_dir)

        return best_match

    def _find_closest_project(self, file_dir: str) -> ProjectState | None:
        """Find the project whose reqstool_path is the closest ancestor of file_dir."""
        best_match: ProjectState | None = None
        best_depth = -1

        norm_dir = os.path.normpath(file_dir)
        for projects in self._folder_projects.values():
            for project in projects:
                reqstool_path = os.path.normpath(project.reqstool_path)
                if norm_dir.startswith(reqstool_path + os.sep) or norm_dir == reqstool_path:
                    depth = reqstool_path.count(os.sep)
                    if depth > best_depth:
                        best_match = project
                        best_depth = depth

        return best_match

    def all_projects(self) -> list[ProjectState]:
        result = []
        for projects in self._folder_projects.values():
            result.extend(projects)
        return result

    def close_all(self) -> None:
        for projects in self._folder_projects.values():
            for project in projects:
                project.close()
        self._folder_projects.clear()

    @staticmethod
    def is_static_yaml(file_uri: str) -> bool:
        file_path = uri_to_path(file_uri)
        return os.path.basename(file_path) in STATIC_YAML_FILES


def uri_to_path(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return uri
