# Copyright © LFV

from unittest.mock import patch

import mcp.server.fastmcp
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.locations.local_location import LocalLocation
from reqstool.mcp import server as mcp_server


class _FakeFastMCP:
    """Stand-in for mcp.server.fastmcp.FastMCP: captures registered tools and the run() call."""

    instances: list["_FakeFastMCP"] = []

    def __init__(self, name):
        self.name = name
        self.settings = type("Settings", (), {})()
        self.tools = {}
        self.run_transport = None
        self.status_result = None
        _FakeFastMCP.instances.append(self)

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def run(self, transport):
        """Simulate a connected client calling a registered tool while the server is up."""
        self.run_transport = transport
        self.status_result = self.tools["get_status"]()


@SVCs("SVC_MCP_0001")
def test_start_server_serves_resolved_dataset(local_testdata_resources_rootdir_w_path):
    """MCP_0001: starting the MCP server builds the project session for the given location
    and exposes its dataset through the registered tools."""
    location = LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))

    with patch.object(mcp.server.fastmcp, "FastMCP", _FakeFastMCP):
        mcp_server.start_server(location=location, transport="stdio")

    fake_mcp = _FakeFastMCP.instances[-1]
    assert fake_mcp.run_transport == "stdio"
    assert fake_mcp.status_result is not None
    assert fake_mcp.status_result["totals"]["requirements"]["total"] > 0
