# Copyright © LFV


from reqstool.common.queries.list import get_list as _get_list
from reqstool.common.queries.list import get_urns_list as _get_urns_list
from reqstool.lsp.project_state import ProjectState


def get_list(project: ProjectState, urn: str | None = None) -> dict:
    if project.repo is None:
        return {"requirements": [], "svcs": [], "mvrs": []}
    return _get_list(project.repo, urn=urn)


def get_urns_list(project: ProjectState) -> list[dict]:
    if project.repo is None:
        return []
    return _get_urns_list(project.repo, project.urn_source_paths)
