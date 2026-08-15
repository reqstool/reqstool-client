# Copyright © LFV


import logging
from typing import Literal

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.project_session import ProjectSession
from reqstool.common.enrichment.enricher import BUILT_IN_PRESETS, enrich_text
from reqstool.common.queries.details import (
    get_mvr_details,
    get_requirement_details,
    get_requirement_status as _get_requirement_status,
    get_requirements_status_all as _get_requirements_status_all,
    get_svc_details,
    get_urn_details as _get_urn_details,
)
from reqstool.common.queries.list import get_mvrs_list, get_requirements_list, get_svcs_list, get_urns_list
from reqstool.locations.location import LocationInterface
from reqstool.services.statistics_service import StatisticsService
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


def start_server(  # noqa: C901
    location: LocationInterface,
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:
        raise ImportError("MCP server requires extra dependencies: pip install 'mcp>=2.0'") from exc

    session = ProjectSession(location)
    session.build()

    if not session.ready:
        raise RuntimeError(f"Failed to load reqstool project: {session.error}")

    if session.repo is None:
        raise RuntimeError("Project session repo is None after successful build")

    @Requirements("MCP_0006", "MCP_0007")
    def _repo() -> RequirementsRepository:
        """Reload the snapshot if the project's input files changed, then return the repository.

        Every tool must resolve the repository through this. Binding it once at startup is
        what let long-lived servers serve a snapshot from before the last build (#437).
        """
        session.ensure_fresh()
        repo = session.repo
        if repo is None:
            raise RuntimeError(f"reqstool project is not loaded: {session.error}")
        return repo

    @Requirements("MCP_0008")
    def _snapshot_info() -> dict:
        fingerprint = session.fingerprint
        return {
            "built_at": session.built_at,
            "reload": "automatic on input change",
            "tracked_files": fingerprint.tracked_file_count if fingerprint is not None else 0,
            "warnings": fingerprint.warnings(primary_urn=session.initial_urn) if fingerprint is not None else [],
        }

    mcp = MCPServer(name="reqstool")

    # SDK 2.x: transport options are run() kwargs instead of server settings.
    run_kwargs: dict = {}
    if transport in ("sse", "streamable-http"):
        run_kwargs.update(host=host, port=port)
    if transport == "streamable-http":
        run_kwargs.update(json_response=True, stateless_http=True)

    @mcp.tool()
    async def list_requirements(urn: str | None = None, lifecycle_state: str | None = None) -> list[dict]:
        """List requirements with id, title, and lifecycle state.
        Filter by urn and/or lifecycle_state (draft|effective|deprecated|obsolete)."""
        return get_requirements_list(_repo(), urn=urn, lifecycle_state=lifecycle_state)

    @mcp.tool()
    async def get_requirement(id: str) -> dict:
        """Get full details for a requirement by ID (e.g. REQ_010)."""
        result = get_requirement_details(id, _repo(), session.urn_source_paths)
        if result is None:
            raise ValueError(f"Requirement {id!r} not found")
        return result

    @mcp.tool()
    async def get_requirements_status(urn: str | None = None, include_post_build: bool = False) -> list[dict]:
        """Batch status for all requirements: id, urn, lifecycle_state, completed, implementation_type,
        automated_tests, manual_tests. Use this to find requirements that are incomplete, partially
        tested, or not yet implemented. Optionally filter by URN. Set include_post_build=True for
        parity with `status --with-post-tests` (scopes to post-build-phase SVCs too)."""
        return _get_requirements_status_all(_repo(), urn=urn, include_post_build=include_post_build)

    @mcp.tool()
    async def list_svcs(urn: str | None = None, lifecycle_state: str | None = None) -> list[dict]:
        """List SVCs with id, title, lifecycle state, and verification type.
        Filter by urn and/or lifecycle_state (draft|effective|deprecated|obsolete)."""
        return get_svcs_list(_repo(), urn=urn, lifecycle_state=lifecycle_state)

    @mcp.tool()
    async def get_svc(id: str) -> dict:
        """Get full details for an SVC by ID (e.g. SVC_010)."""
        result = get_svc_details(id, _repo(), session.urn_source_paths)
        if result is None:
            raise ValueError(f"SVC {id!r} not found")
        return result

    @mcp.tool()
    async def list_mvrs(urn: str | None = None, passed: bool | None = None) -> list[dict]:
        """List MVRs with id and passed status. Filter by urn and/or passed (True|False)."""
        return get_mvrs_list(_repo(), urn=urn, passed=passed)

    @mcp.tool()
    async def get_mvr(id: str) -> dict:
        """Get full details for an MVR by ID."""
        result = get_mvr_details(id, _repo(), session.urn_source_paths)
        if result is None:
            raise ValueError(f"MVR {id!r} not found")
        return result

    @mcp.tool()
    async def get_status() -> dict:
        """Get overall traceability status — completion per requirement, test totals.

        The `snapshot` field reports when the served data was parsed and warns about
        configured test-result patterns that matched no files (an unbuilt or partially
        built project reports zero tests, which is not the same as having no tests)."""
        status = StatisticsService(_repo()).to_status_dict()
        status["snapshot"] = _snapshot_info()
        return status

    @mcp.tool()
    async def refresh() -> dict:
        """Force an immediate reload of the project from disk.

        Reloading is automatic when input files change, so this is only needed to reload
        unconditionally — after a build, for instance — or to confirm what is being served."""
        session.build()
        if not session.ready:
            raise RuntimeError(f"Failed to reload reqstool project: {session.error}")
        return _snapshot_info()

    @mcp.tool()
    async def get_requirement_status(id: str, include_post_build: bool = False) -> dict:
        """Status check for one requirement: lifecycle_state, completed, implementation_type,
        automated_tests, manual_tests. Set include_post_build=True for parity with
        `status --with-post-tests` (scopes to post-build-phase SVCs too)."""
        result = _get_requirement_status(id, _repo(), include_post_build=include_post_build)
        if result is None:
            raise ValueError(f"Requirement {id!r} not found")
        return result

    @mcp.tool()
    async def list_annotations(urn: str | None = None) -> list[dict]:
        """List implementation annotations (@Requirements) found in source code. Optionally filter by URN."""
        impl_annotations = _repo().get_annotations_impls(urn=urn)
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
    async def list_urns() -> list[dict]:
        """List all URNs in the project graph with variant, title, url, location, and file paths."""
        return get_urns_list(_repo(), session.urn_source_paths)

    @mcp.tool()
    async def get_urn_details(urn: str) -> dict:
        """Get details for a URN: variant, title, location, file paths, and entity counts."""
        result = _get_urn_details(urn, _repo(), session.urn_source_paths)
        if result is None:
            raise ValueError(f"URN {urn!r} not found")
        return result

    @mcp.tool()
    async def enrich_document(content: str, preset: str) -> str:
        """Enrich an OpenSpec document by resolving requirement/SVC/MVR IDs.

        Injects titles and further fields next to each known ID according to the
        named preset. Both arguments are required.

        Presets: openspec:spec, openspec:delta-spec, openspec:design,
                 openspec:proposal, openspec:tasks
        """
        if preset not in BUILT_IN_PRESETS:
            raise ValueError(f"Unknown preset {preset!r}. Valid: {sorted(BUILT_IN_PRESETS)}")
        config = BUILT_IN_PRESETS[preset]
        repo = _repo()
        return enrich_text(content, repo.get_all_requirements(), repo.get_all_svcs(), repo.get_all_mvrs(), config)

    try:
        logger.info("Starting reqstool MCP server (transport=%s, host=%s, port=%s)", transport, host, port)
        mcp.run(transport=transport, **run_kwargs)
    finally:
        session.close()
