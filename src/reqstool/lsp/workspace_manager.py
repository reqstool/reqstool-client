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
        norm_file = os.path.normpath(file_path)
        best_match: ProjectState | None = None
        best_depth = -1

        # First: exact match — file is under the reqstool_path directory itself
        for projects in self._folder_projects.values():
            for project in projects:
                reqstool_path = os.path.normpath(project.reqstool_path)
                if norm_file.startswith(reqstool_path + os.sep) or norm_file == reqstool_path:
                    depth = reqstool_path.count(os.sep)
                    if depth > best_depth:
                        best_match = project
                        best_depth = depth

        if best_match is not None:
            return best_match

        # Fallback: file is anywhere within the workspace folder that contains the project
        # (e.g. a Java source file in src/ belonging to a project whose reqstool_path is docs/reqstool/)
        for folder_uri, projects in self._folder_projects.items():
            if not projects:
                continue
            folder_path = uri_to_path(folder_uri)
            norm_folder = os.path.normpath(folder_path)
            if norm_file.startswith(norm_folder + os.sep) or norm_file == norm_folder:
                return max(projects, key=lambda p: os.path.normpath(p.reqstool_path).count(os.sep))

        return None

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
