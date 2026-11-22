# Copyright © LFV

from mcp.server.mcpserver.exceptions import ToolError
import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from tests.unit.reqstool.mcp.test_server_freshness import _serve, project_copy  # noqa: F401


@SVCs("SVC_MCP_0009")
def test_search_hits_carry_the_shared_status_verdict(project_copy):  # noqa: F811
    async def scenario(tools):
        hits = (await tools["search"]("Title REQ_101", kinds=["requirement"]))["results"]
        status = {s["id"]: s for s in await tools["get_requirements_status"]()}
        return hits, status

    hits, status = _serve(project_copy, scenario)

    assert hits and hits[0]["id"] == "REQ_101"
    assert hits[0]["completed"] == status["REQ_101"]["completed"]
    assert {"kind", "urn", "title", "snippet", "lifecycle_state"} <= hits[0].keys()


@SVCs("SVC_MCP_0009")
def test_search_follows_the_reloaded_snapshot(project_copy):  # noqa: F811
    async def scenario(tools):
        before = (await tools["search"]("Zebra"))["results"]
        req = project_copy / "requirements.yml"
        req.write_text(req.read_text().replace("Title REQ_101", "Zebra REQ_101"))
        after = (await tools["search"]("Zebra"))["results"]
        return before, after

    before, after = _serve(project_copy, scenario)

    assert before == []
    assert [h["id"] for h in after] == ["REQ_101"]


@SVCs("SVC_MCP_0009")
def test_search_rejects_unknown_kind(project_copy):  # noqa: F811
    async def scenario(tools):
        with pytest.raises(ToolError, match="Unknown kind"):
            await tools["search"]("x", kinds=["bogus"])
        return True

    assert _serve(project_copy, scenario)
