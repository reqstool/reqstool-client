# Copyright © LFV


import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

FIXTURE_DIR = str(Path(__file__).resolve().parents[3] / "fixtures" / "reqstool-regression-python")

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


@pytest.fixture(scope="session")
def fixture_dir():
    import os

    assert os.path.isdir(FIXTURE_DIR), f"Fixture directory not found: {FIXTURE_DIR}"
    return FIXTURE_DIR


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(fixture_dir):
    """Session-scoped async fixture: start MCP server, initialize session, yield, shutdown.

    The entire stdio_client + ClientSession lifecycle runs inside a single asyncio Task
    so that anyio cancel scopes are always entered and exited by the same task.
    """
    ready: asyncio.Queue = asyncio.Queue()
    done = asyncio.Event()

    async def _lifecycle():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "reqstool.command", "mcp", "local", "-p", fixture_dir],
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
