# Copyright © LFV


import logging

from reqstool.common.project_session import ProjectSession
from reqstool.common.queries.details import get_mvr_details, get_requirement_details, get_svc_details
from reqstool.common.queries.list import get_list
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
    def list_requirements() -> list[dict]:
        """List all requirements with id, title, and lifecycle state."""
        return get_list(repo)["requirements"]

    @mcp.tool()
    def get_requirement(id: str) -> dict:
        """Get full details for a requirement by ID (e.g. REQ_010)."""
        result = get_requirement_details(id, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"Requirement {id!r} not found")
        return result

    @mcp.tool()
    def list_svcs() -> list[dict]:
        """List all SVCs with id, title, lifecycle state, and verification type."""
        return get_list(repo)["svcs"]

    @mcp.tool()
    def get_svc(id: str) -> dict:
        """Get full details for an SVC by ID (e.g. SVC_010)."""
        result = get_svc_details(id, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"SVC {id!r} not found")
        return result

    @mcp.tool()
    def list_mvrs() -> list[dict]:
        """List all MVRs with id and passed status."""
        return get_list(repo)["mvrs"]

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
        result = get_requirement_details(id, repo, urn_source_paths)
        if result is None:
            raise ValueError(f"Requirement {id!r} not found")
        test_summary = {"passed": 0, "failed": 0, "skipped": 0, "missing": 0}
        for svc in result.get("svcs", []):
            for key in test_summary:
                test_summary[key] += svc.get("test_summary", {}).get(key, 0)
        # skipped tests are not counted as failures; a requirement only "meets" if
        # it has at least one implementation and no failed or missing test results
        all_passing = test_summary["failed"] == 0 and test_summary["missing"] == 0
        return {
            "id": result["id"],
            "lifecycle_state": result["lifecycle"]["state"],
            "implementation": result["implementation"],
            "test_summary": test_summary,
            "meets_requirements": result["implementation"] != "not_implemented" and all_passing,
        }

    @mcp.tool()
    def list_annotations() -> list[dict]:
        """List all implementation annotations (@Requirements) found in source code."""
        impl_annotations = repo.get_annotations_impls()
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

    try:
        mcp.run()
    finally:
        session.close()
