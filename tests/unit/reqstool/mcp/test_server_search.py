# Copyright © LFV

from mcp.server.mcpserver.exceptions import ToolError
import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.storage import search_index
from reqstool.storage.requirements_repository import RequirementsRepository
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


@SVCs("SVC_MCP_0009")
def test_search_rejects_unknown_lifecycle_state_and_urn(project_copy):  # noqa: F811
    async def scenario(tools):
        with pytest.raises(ToolError, match="lifecycle_state"):
            await tools["search"]("Title", lifecycle_state="effectve")
        with pytest.raises(ToolError, match="Unknown urn"):
            await tools["search"]("Title", urn="no-such-urn")
        return True

    assert _serve(project_copy, scenario)


@SVCs("SVC_MCP_0009")
def test_search_urn_and_lifecycle_filters(project_copy):  # noqa: F811
    async def scenario(tools):
        in_urn = (await tools["search"]("Title", urn="ms-101"))["results"]
        effective = (await tools["search"]("Title", lifecycle_state="effective"))["results"]
        obsolete = (await tools["search"]("Title", lifecycle_state="obsolete"))["results"]
        return in_urn, effective, obsolete

    in_urn, effective, obsolete = _serve(project_copy, scenario)

    assert in_urn and {h["urn"] for h in in_urn} == {"ms-101"}
    assert effective and all(h["lifecycle_state"] == "effective" for h in effective)
    assert obsolete == []


@SVCs("SVC_MCP_0009")
def test_search_limit_is_clamped_and_blank_query_is_empty(project_copy):  # noqa: F811
    async def scenario(tools):
        one = (await tools["search"]("Title", limit=0))["results"]
        many = (await tools["search"]("Title", limit=10_000))["results"]
        blank = (await tools["search"]("  !! "))["results"]
        return one, many, blank

    one, many, blank = _serve(project_copy, scenario)

    assert len(one) == 1
    assert 1 < len(many) <= 100
    assert blank == []


@SVCs("SVC_MCP_0009")
def test_search_reports_unranked_results_when_fts5_is_missing(project_copy, monkeypatch):  # noqa: F811
    monkeypatch.setattr(search_index, "_CREATE", "CREATE VIRTUAL TABLE search_fts USING no_such_module(x)")

    async def scenario(tools):
        return await tools["search"]("REQ_101")

    out = _serve(project_copy, scenario)

    assert "unranked" in out["note"]
    assert "REQ_101" in [h["id"] for h in out["results"]]


@SVCs("SVC_MCP_0009")
def test_search_does_not_load_every_requirement(project_copy, monkeypatch):  # noqa: F811
    def boom(self, *a, **kw):
        raise AssertionError("search must look up its hits, not load all requirements")

    async def scenario(tools):
        # patched after startup: building the snapshot legitimately reads every requirement
        monkeypatch.setattr(RequirementsRepository, "get_all_requirements", boom)
        return (await tools["search"]("Title REQ_101", kinds=["requirement"]))["results"]

    assert _serve(project_copy, scenario)[0]["id"] == "REQ_101"
