# Copyright © LFV


import logging

from reqstool.common.project_session import ProjectSession
from reqstool.common.queries.details import (
    get_mvr_details,
    get_requirement_details,
    get_requirement_status as _get_requirement_status,
    get_svc_details,
    get_urn_details as _get_urn_details,
)
from reqstool.common.queries.list import get_mvrs_list, get_requirements_list, get_svcs_list, get_urns_list
from reqstool.locations.location import LocationInterface
from reqstool.services.statistics_service import StatisticsService
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


def start_server(location: LocationInterface) -> None:  # noqa: C901
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError("MCP server requires extra dependencies: pip install 'mcp>=1.0'") from exc

    session = ProjectSession(location)
    session.build()

    if not session.ready:
        raise RuntimeError(f"Failed to load reqstool project: {session.error}")

    if session.repo is None:
        raise RuntimeError("Project session repo is None after successful build")
    repo: RequirementsRepository = session.repo
    urn_source_paths = session.urn_source_paths

    mcp = FastMCP("reqstool")

    @mcp.tool()
    def list_requirements(urn: str | None = None) -> list[dict]:
        """List requirements with id, title, and lifecycle state. Optionally filter by URN."""
        return get_requirements_list(repo, urn=urn)

    @mcp.tool()
    def get_requirement(id: str) -> dict:
        """Get full details for a requirement by ID (e.g. REQ_010)."""
        result = get_requirement_details(id, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"Requirement {id!r} not found")
        return result

    @mcp.tool()
    def list_svcs(urn: str | None = None) -> list[dict]:
        """List SVCs with id, title, lifecycle state, and verification type. Optionally filter by URN."""
        return get_svcs_list(repo, urn=urn)

    @mcp.tool()
    def get_svc(id: str) -> dict:
        """Get full details for an SVC by ID (e.g. SVC_010)."""
        result = get_svc_details(id, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"SVC {id!r} not found")
        return result

    @mcp.tool()
    def list_mvrs(urn: str | None = None) -> list[dict]:
        """List MVRs with id and passed status. Optionally filter by URN."""
        return get_mvrs_list(repo, urn=urn)

    @mcp.tool()
    def get_mvr(id: str) -> dict:
        """Get full details for an MVR by ID."""
        result = get_mvr_details(id, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"MVR {id!r} not found")
        return result

    @mcp.tool()
    def get_status() -> dict:
        """Get overall traceability status — completion per requirement, test totals."""
        return StatisticsService(repo).to_status_dict()

    @mcp.tool()
    def get_requirement_status(id: str) -> dict:
        """Quick status check for one requirement: lifecycle state, implementation status, test summary."""
        result = _get_requirement_status(id, repo)
        if result is None:
            raise ValueError(f"Requirement {id!r} not found")
        return result

    @mcp.tool()
    def list_annotations(urn: str | None = None) -> list[dict]:
        """List implementation annotations (@Requirements) found in source code. Optionally filter by URN."""
        impl_annotations = repo.get_annotations_impls(urn=urn)
        result = []
        for urn_id, ann_list in impl_annotations.items():
            for ann in ann_list:
                result.append(
                    {
                        "req_id": urn_id.id,
                        "req_urn": urn_id.urn,
                        "element_kind": ann.element_kind,
                        "fqn": ann.fully_qualified_name,
                    }
                )
        return result

    @mcp.tool()
    def list_urns() -> list[dict]:
        """List all URNs in the project graph with variant, title, url, location, and file paths."""
        return get_urns_list(repo, urn_source_paths)

    @mcp.tool()
    def get_urn_details(urn: str) -> dict:
        """Get details for a URN: variant, title, location, file paths, and entity counts."""
        result = _get_urn_details(urn, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"URN {urn!r} not found")
        return result

    try:
        mcp.run()
    finally:
        session.close()
