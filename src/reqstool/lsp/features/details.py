# Copyright © LFV


from reqstool.common.queries.details import get_mvr_details as _get_mvr_details
from reqstool.common.queries.details import get_requirement_details as _get_requirement_details
from reqstool.common.queries.details import get_svc_details as _get_svc_details
from reqstool.common.queries.details import get_urn_details as _get_urn_details
from reqstool.lsp.project_state import ProjectState


def get_requirement_details(raw_id: str, project: ProjectState) -> dict | None:
    return _get_requirement_details(raw_id, project.repo, project.urn_source_paths)


def get_svc_details(raw_id: str, project: ProjectState) -> dict | None:
    return _get_svc_details(raw_id, project.repo, project.urn_source_paths)


def get_mvr_details(raw_id: str, project: ProjectState) -> dict | None:
    return _get_mvr_details(raw_id, project.repo, project.urn_source_paths)


def get_urn_details(urn: str, project: ProjectState) -> dict | None:
    return _get_urn_details(urn, project.repo, project.urn_source_paths)
