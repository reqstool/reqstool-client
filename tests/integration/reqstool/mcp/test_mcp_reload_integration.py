# Copyright © LFV

"""End-to-end proof that a running MCP server follows the project it was pointed at.

The shared `mcp_session` fixture serves the pristine fixture directory, so these tests run
their own server against a writable copy — the point is to change files underneath a live
server, which is exactly what a build does while an AI harness keeps the server spawned.
"""

import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from reqstool_python_decorators.decorators.decorators import SVCs

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "reqstool-regression-python"

ADDED_IMPLEMENTATION_FQN = "reqstool_regression.added.AfterServerStartup"


def _parse_result(result) -> list | dict:
    blocks = [json.loads(b.text) for b in result.content if hasattr(b, "text")]
    return blocks if len(blocks) != 1 else blocks[0]


@pytest.fixture(scope="module")
def mutable_project(tmp_path_factory) -> Path:
    dst = tmp_path_factory.mktemp("reqstool-reload") / "project"
    shutil.copytree(FIXTURE_DIR, dst)
    return dst


@pytest_asyncio.fixture(loop_scope="session", scope="module")
async def reload_session(mutable_project):
    """A server spawned against the writable copy, kept alive across the tests below."""
    ready: asyncio.Queue = asyncio.Queue()
    done = asyncio.Event()

    async def _lifecycle():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "reqstool.command", "mcp", "local", "-p", str(mutable_project)],
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await ready.put(session)
                    await done.wait()
        except Exception as exc:
            await ready.put(exc)

    task = asyncio.create_task(_lifecycle())
    result = await ready.get()
    if isinstance(result, Exception):
        raise result

    yield result

    done.set()
    await task


@SVCs("SVC_MCP_0006")
async def test_annotations_written_after_startup_are_served(reload_session, mutable_project):
    """#437: the server answered from its spawn-time snapshot for as long as it stayed up."""
    before = _parse_result(await reload_session.call_tool("list_annotations", {}))
    assert not any(a["fqn"] == ADDED_IMPLEMENTATION_FQN for a in before)

    annotations = mutable_project / "annotations.yml"
    original = annotations.read_text()
    existing = '        fullyQualifiedName: "requirements_example.RequirementsExample"\n'
    assert existing in original
    annotations.write_text(
        original.replace(
            existing,
            f'{existing}      - elementKind: "CLASS"\n        fullyQualifiedName: "{ADDED_IMPLEMENTATION_FQN}"\n',
            1,
        )
    )

    after = _parse_result(await reload_session.call_tool("list_annotations", {}))

    assert any(a["fqn"] == ADDED_IMPLEMENTATION_FQN for a in after)
    assert len(after) > len(before)


@SVCs("SVC_MCP_0008")
async def test_get_status_reports_the_snapshot_it_answered_from(reload_session):
    status = _parse_result(await reload_session.call_tool("get_status", {}))

    assert status["snapshot"]["built_at"] is not None
    assert status["snapshot"]["tracked_files"] > 0


@SVCs("SVC_MCP_0006")
async def test_refresh_tool_reloads_on_demand(reload_session):
    before = _parse_result(await reload_session.call_tool("get_status", {}))["snapshot"]

    refreshed = _parse_result(await reload_session.call_tool("refresh", {}))

    assert refreshed["built_at"] != before["built_at"]


@SVCs("SVC_MCP_0007")
async def test_a_project_that_no_longer_parses_is_an_error_not_a_stale_answer(reload_session, mutable_project):
    requirements = mutable_project / "requirements.yml"
    original = requirements.read_text()
    requirements.write_text(": this is not: [ valid yaml")

    try:
        result = await reload_session.call_tool("get_status", {})
        assert result.is_error
        assert "reloading them failed" in str(result.content)
    finally:
        requirements.write_text(original)

    assert not (await reload_session.call_tool("get_status", {})).is_error
