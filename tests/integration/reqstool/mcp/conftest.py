# Copyright © LFV

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

FIXTURE_DIR = str(Path(__file__).resolve().parents[3] / "fixtures" / "reqstool-regression-python")

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


@pytest.fixture(scope="session")
def fixture_dir():
    import os

    assert os.path.isdir(FIXTURE_DIR), f"Fixture directory not found: {FIXTURE_DIR}"
    return FIXTURE_DIR


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def mcp_session(fixture_dir):
    """Module-scoped async fixture: start MCP server, initialize session, yield, shutdown."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "reqstool.command", "mcp", "local", "-p", fixture_dir],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
