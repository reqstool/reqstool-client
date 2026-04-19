import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from lsprotocol import types
from pygls.lsp.client import BaseLanguageClient

FIXTURE_DIR = str(Path(__file__).resolve().parents[3] / "fixtures" / "reqstool-regression-python")


class ReqstoolTestClient(BaseLanguageClient):
    """LSP client that collects publishDiagnostics notifications."""

    def __init__(self):
        super().__init__(name="reqstool-test-client", version="0.0.1")
        self.diagnostics: dict[str, list[types.Diagnostic]] = {}
        self._diagnostics_version: int = 0
        self._diagnostics_event = asyncio.Event()

        @self.feature(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
        def on_publish_diagnostics(params: types.PublishDiagnosticsParams):
            self.diagnostics[params.uri] = params.diagnostics
            self._diagnostics_version += 1
            self._diagnostics_event.set()

    def clear_diagnostics(self):
        """Clear cached diagnostics so the next wait_for_diagnostics blocks until fresh data arrives."""
        self.diagnostics.clear()
        self._diagnostics_event.clear()

    async def wait_for_diagnostics(self, uri: str, timeout: float = 10.0) -> list[types.Diagnostic]:
        """Wait until diagnostics arrive for the given URI."""
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            if uri in self.diagnostics:
                return self.diagnostics[uri]
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return self.diagnostics.get(uri, [])
            self._diagnostics_event.clear()
            try:
                await asyncio.wait_for(self._diagnostics_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                return self.diagnostics.get(uri, [])


@pytest.fixture(scope="session")
def fixture_dir():
    """Path to the regression-python fixture directory."""
    assert os.path.isdir(FIXTURE_DIR), f"Fixture directory not found: {FIXTURE_DIR}"
    return FIXTURE_DIR


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def lsp_client(fixture_dir):
    """Module-scoped async fixture: starts LSP server, initializes, yields client, shuts down."""
    client = ReqstoolTestClient()

    await client.start_io(sys.executable, "-m", "reqstool.command", "lsp")

    workspace_folder = types.WorkspaceFolder(
        uri=Path(fixture_dir).as_uri(),
        name="reqstool-regression-python",
    )

    result = await client.initialize_async(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(
                text_document=types.TextDocumentClientCapabilities(
                    hover=types.HoverClientCapabilities(),
                    completion=types.CompletionClientCapabilities(),
                    definition=types.DefinitionClientCapabilities(),
                    document_symbol=types.DocumentSymbolClientCapabilities(),
                    publish_diagnostics=types.PublishDiagnosticsClientCapabilities(),
                ),
                workspace=types.WorkspaceClientCapabilities(
                    workspace_folders=True,
                ),
            ),
            root_uri=Path(fixture_dir).as_uri(),
            workspace_folders=[workspace_folder],
        )
    )

    # Send initialized notification to trigger project discovery
    client.initialized(types.InitializedParams())

    # Give the server time to discover and build the project
    await asyncio.sleep(2)

    yield client, result

    await client.shutdown_async(None)
    client.exit(None)
    await asyncio.sleep(0.5)
