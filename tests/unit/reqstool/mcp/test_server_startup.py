# Copyright © LFV


import asyncio
from unittest.mock import patch

import mcp.server.mcpserver
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.locations.local_location import LocalLocation
from reqstool.mcp import server as mcp_server


class _FakeMCPServer:
    """Stand-in for mcp.server.mcpserver.MCPServer: captures registered tools and the run() call."""

    instances: list["_FakeMCPServer"] = []

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.tools = {}
        self.run_transport = None
        self.run_kwargs = None
        self.status_result = None
        _FakeMCPServer.instances.append(self)

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def run(self, transport, **kwargs):
        """Simulate a connected client calling a registered tool while the server is up."""
        self.run_transport = transport
        self.run_kwargs = kwargs
        # Tools are async so they execute on the event loop thread (SQLite affinity).
        self.status_result = asyncio.run(self.tools["get_status"]())


@SVCs("SVC_MCP_0001")
def test_start_server_serves_resolved_dataset(local_testdata_resources_rootdir_w_path):
    """MCP_0001: starting the MCP server builds the project session for the given location
    and exposes its dataset through the registered tools."""
    location = LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))

    with patch.object(mcp.server.mcpserver, "MCPServer", _FakeMCPServer):
        mcp_server.start_server(location=location, transport="stdio")

    fake_mcp = _FakeMCPServer.instances[-1]
    assert fake_mcp.run_transport == "stdio"
    assert fake_mcp.run_kwargs == {}
    assert fake_mcp.status_result is not None
    assert fake_mcp.status_result["totals"]["requirements"]["total"] > 0


@SVCs("SVC_MCP_0002")
def test_start_server_streamable_http_configures_settings(local_testdata_resources_rootdir_w_path):
    """MCP_0002: the streamable-HTTP transport is served as stateless JSON responses on the
    configured host and port."""
    location = LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))

    with patch.object(mcp.server.mcpserver, "MCPServer", _FakeMCPServer):
        mcp_server.start_server(location=location, transport="streamable-http", host="0.0.0.0", port=9000)

    fake_mcp = _FakeMCPServer.instances[-1]
    assert fake_mcp.run_transport == "streamable-http"
    assert fake_mcp.run_kwargs == {"host": "0.0.0.0", "port": 9000, "json_response": True, "stateless_http": True}
