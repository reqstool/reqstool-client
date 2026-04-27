# Copyright © LFV


import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "reqstool-regression-python"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


@pytest_asyncio.fixture(loop_scope="session", scope="module")
async def autodetect_mcp_session(tmp_path_factory):
    """Launch `reqstool mcp` (no source) from a dir containing .reqstool-ai.yaml."""
    project_root = tmp_path_factory.mktemp("autodetect_project")
    config = project_root / ".reqstool-ai.yaml"
    config.write_text(f"system:\n  path: {FIXTURE_DIR}\n")

    ready: asyncio.Queue = asyncio.Queue()
    done = asyncio.Event()

    async def _lifecycle():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "reqstool.command", "mcp"],
            cwd=str(project_root),
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


async def test_autodetect_serves_tools(autodetect_mcp_session):
    """Bare `reqstool mcp` resolves dataset from .reqstool-ai.yaml and serves tools."""
    result = await autodetect_mcp_session.list_tools()
    tool_names = {t.name for t in result.tools}
    assert "list_requirements" in tool_names
    assert "get_requirement" in tool_names
