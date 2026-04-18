# Copyright © LFV


import json

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

# IDs present in the reqstool-regression-python fixture
KNOWN_REQ_ID = "REQ_PASS"
KNOWN_SVC_ID = "SVC_010"


def _parse_result(result) -> list | dict:
    """FastMCP returns each list item as a separate TextContent block."""
    blocks = [json.loads(b.text) for b in result.content if hasattr(b, "text")]
    return blocks if len(blocks) != 1 else blocks[0]


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------


async def test_list_tools(mcp_session):
    """Server advertises all 9 expected tools."""
    result = await mcp_session.list_tools()
    tool_names = {t.name for t in result.tools}
    expected = {
        "list_requirements",
        "get_requirement",
        "list_svcs",
        "get_svc",
        "list_mvrs",
        "get_mvr",
        "get_status",
        "get_requirement_status",
        "list_annotations",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


# ---------------------------------------------------------------------------
# list_requirements
# ---------------------------------------------------------------------------


async def test_list_requirements(mcp_session):
    result = await mcp_session.call_tool("list_requirements", {})
    reqs = _parse_result(result)
    assert isinstance(reqs, list)
    assert len(reqs) > 0
    for req in reqs:
        assert "id" in req
        assert "title" in req
        assert "lifecycle_state" in req


# ---------------------------------------------------------------------------
# get_requirement
# ---------------------------------------------------------------------------


async def test_get_requirement_known(mcp_session):
    result = await mcp_session.call_tool("get_requirement", {"id": KNOWN_REQ_ID})
    req = _parse_result(result)
    assert req["id"] == KNOWN_REQ_ID
    assert req["type"] == "requirement"
    assert "svcs" in req
    assert "implementations" in req
    assert "lifecycle" in req
    assert "source_paths" in req


async def test_get_requirement_not_found(mcp_session):
    result = await mcp_session.call_tool("get_requirement", {"id": "REQ_NONEXISTENT"})
    assert result.isError


# ---------------------------------------------------------------------------
# list_svcs
# ---------------------------------------------------------------------------


async def test_list_svcs(mcp_session):
    result = await mcp_session.call_tool("list_svcs", {})
    svcs = _parse_result(result)
    assert isinstance(svcs, list)
    assert len(svcs) > 0
    for svc in svcs:
        assert "id" in svc
        assert "title" in svc
        assert "lifecycle_state" in svc
        assert "verification" in svc


# ---------------------------------------------------------------------------
# get_svc
# ---------------------------------------------------------------------------


async def test_get_svc_known(mcp_session):
    result = await mcp_session.call_tool("get_svc", {"id": KNOWN_SVC_ID})
    svc = _parse_result(result)
    assert svc["id"] == KNOWN_SVC_ID
    assert svc["type"] == "svc"
    assert "test_summary" in svc
    assert "requirement_ids" in svc
    assert "mvrs" in svc


async def test_get_svc_not_found(mcp_session):
    result = await mcp_session.call_tool("get_svc", {"id": "SVC_NONEXISTENT"})
    assert result.isError


# ---------------------------------------------------------------------------
# list_mvrs / get_mvr
# ---------------------------------------------------------------------------


async def test_list_mvrs(mcp_session):
    result = await mcp_session.call_tool("list_mvrs", {})
    mvrs = _parse_result(result)
    assert isinstance(mvrs, list)
    for mvr in mvrs:
        assert "id" in mvr
        assert "passed" in mvr


async def test_get_mvr_not_found(mcp_session):
    result = await mcp_session.call_tool("get_mvr", {"id": "MVR_NONEXISTENT"})
    assert result.isError


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


async def test_get_status(mcp_session):
    result = await mcp_session.call_tool("get_status", {})
    status = _parse_result(result)
    assert "requirements" in status
    assert "totals" in status


# ---------------------------------------------------------------------------
# get_requirement_status
# ---------------------------------------------------------------------------


async def test_get_requirement_status(mcp_session):
    result = await mcp_session.call_tool("get_requirement_status", {"id": KNOWN_REQ_ID})
    status = _parse_result(result)
    assert status["id"] == KNOWN_REQ_ID
    assert "lifecycle_state" in status
    assert "implementation" in status
    assert "test_summary" in status
    assert "meets_requirements" in status
    assert isinstance(status["meets_requirements"], bool)


async def test_get_requirement_status_not_found(mcp_session):
    result = await mcp_session.call_tool("get_requirement_status", {"id": "REQ_NONEXISTENT"})
    assert result.isError


# ---------------------------------------------------------------------------
# list_annotations
# ---------------------------------------------------------------------------


async def test_list_annotations(mcp_session):
    result = await mcp_session.call_tool("list_annotations", {})
    annotations = _parse_result(result)
    assert isinstance(annotations, list)
    assert len(annotations) > 0
    for ann in annotations:
        assert "req_id" in ann
        assert "req_urn" in ann
        assert "element_kind" in ann
        assert "fqn" in ann
