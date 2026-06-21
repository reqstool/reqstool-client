# Copyright © LFV

from unittest.mock import patch

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.lsp.server import server, start_server


@SVCs("SVC_LSP_0001")
def test_start_server_starts_stdio_transport_by_default():
    """LSP_0001: `start_server()` starts the language server, ready to accept client connections."""
    with patch.object(server, "start_io") as mock_start_io, patch.object(server, "start_tcp") as mock_start_tcp:
        start_server()

    mock_start_io.assert_called_once()
    mock_start_tcp.assert_not_called()
