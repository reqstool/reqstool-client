# Copyright © LFV


from reqstool.common.queries.list import get_list as _get_list
from reqstool.lsp.project_state import ProjectState


def get_list(project: ProjectState) -> dict:
    if project.repo is None:
        return {"requirements": [], "svcs": [], "mvrs": []}
    return _get_list(project.repo)
