# Copyright © LFV

"""The MCP server serves a long-lived snapshot; these tests drive it while the project changes.

Tools are exercised from inside the fake server's run() because start_server() closes the
session as soon as run() returns — the same window a real client operates in.
"""

import asyncio
import shutil
from unittest.mock import patch

import mcp.server.mcpserver
import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.exceptions import SnapshotReloadError
from reqstool.locations.local_location import LocalLocation
from reqstool.mcp import server as mcp_server

ANNOTATIONS_WITH_EXTRA_IMPL = """\
---
requirement_annotations:
  implementations:
    REQ_101:
      - elementKind: "CLASS"
        fullyQualifiedName: "com.example.RequirementsExample"
      - elementKind: "METHOD"
        fullyQualifiedName: "com.example.RequirementsExample.addedAfterStartup"
    REQ_201:
      - elementKind: "METHOD"
        fullyQualifiedName: "com.example.RequirementsExample.someMethod"
"""


class _DrivenMCPServer:
    """Stand-in for MCPServer that hands the registered tools to a test-supplied scenario."""

    instances: list["_DrivenMCPServer"] = []
    scenario = None

    def __init__(self, name=None, **kwargs):
        self.tools = {}
        self.result = None
        _DrivenMCPServer.instances.append(self)

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def run(self, transport, **kwargs):
        # Tools are async so they execute on the event loop thread (SQLite affinity).
        self.result = asyncio.run(_DrivenMCPServer.scenario(self.tools))


def _serve(project_path, scenario):
    """Start the server against project_path, run scenario(tools) against it, return its value."""
    _DrivenMCPServer.scenario = scenario
    _DrivenMCPServer.instances.clear()
    with patch.object(mcp.server.mcpserver, "MCPServer", _DrivenMCPServer):
        mcp_server.start_server(location=LocalLocation(path=str(project_path)), transport="stdio")
    return _DrivenMCPServer.instances[-1].result


@pytest.fixture
def project_copy(tmp_path, local_testdata_resources_rootdir_w_path):
    dst = tmp_path / "ms-101"
    shutil.copytree(local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"), dst)
    return dst


@SVCs("SVC_MCP_0006")
def test_tools_serve_the_current_project_not_the_startup_snapshot(project_copy):
    """#437: a server spawned before a build kept answering from its spawn-time snapshot."""

    async def scenario(tools):
        before = await tools["list_annotations"]()

        (project_copy / "annotations.yml").write_text(ANNOTATIONS_WITH_EXTRA_IMPL)

        after = await tools["list_annotations"]()
        return before, after

    before, after = _serve(project_copy, scenario)

    assert len(after) > len(before)
    assert any(a["fqn"].endswith("addedAfterStartup") for a in after)
    assert not any(a["fqn"].endswith("addedAfterStartup") for a in before)


@SVCs("SVC_MCP_0006")
def test_refresh_tool_reloads_unconditionally(project_copy):
    async def scenario(tools):
        first = await tools["get_status"]()
        refreshed = await tools["refresh"]()
        return first["snapshot"], refreshed

    first_snapshot, refreshed = _serve(project_copy, scenario)

    assert refreshed["built_at"] != first_snapshot["built_at"]
    assert refreshed["tracked_files"] == first_snapshot["tracked_files"]


@SVCs("SVC_MCP_0007")
def test_a_tool_errors_when_the_changed_project_cannot_be_reloaded(project_copy):
    """A well-formed answer from a snapshot known to be superseded is the dangerous case."""

    async def scenario(tools):
        (project_copy / "requirements.yml").write_text(": this is not: [ valid yaml")

        with pytest.raises(SnapshotReloadError, match="sources changed but reloading them failed"):
            await tools["get_status"]()
        with pytest.raises(SnapshotReloadError):
            await tools["list_requirements"]()
        return True

    assert _serve(project_copy, scenario) is True


@SVCs("SVC_MCP_0008")
def test_get_status_reports_when_its_data_was_parsed(project_copy):
    async def scenario(tools):
        return await tools["get_status"]()

    status = _serve(project_copy, scenario)

    assert status["snapshot"]["built_at"] is not None
    assert status["snapshot"]["tracked_files"] > 0
    assert status["snapshot"]["warnings"] == []


@SVCs("SVC_MCP_0008")
def test_get_status_warns_when_no_test_results_were_found(project_copy):
    """Zero tests because nothing was built must be distinguishable from zero tests."""
    shutil.rmtree(project_copy / "test_results")

    async def scenario(tools):
        return await tools["get_status"]()

    status = _serve(project_copy, scenario)

    assert status["totals"]["automated_tests"]["passed"] == 0
    assert len(status["snapshot"]["warnings"]) == 1
    assert "matched no files" in status["snapshot"]["warnings"][0]
