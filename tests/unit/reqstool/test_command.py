# Copyright © LFV

from unittest.mock import MagicMock, patch

import argparse
import io
import sys

import pytest

from reqstool.command import Command, main
from reqstool.commands.exit_codes import (
    EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED,
    EXIT_CODE_ARTIFACT_ERROR,
    EXIT_CODE_MISSING_REQUIREMENTS_FILE,
)
from reqstool.common.exceptions import ArtifactDownloadError, MissingRequirementsFileError
from reqstool.locations.git_location import GitLocation
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.pypi_location import PypiLocation
from reqstool.locations.local_npm_location import LocalNpmLocation
from reqstool.locations.npm_location import NpmLocation
from reqstool_python_decorators.decorators.decorators import SVCs


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


@SVCs("SVC_REPORT_0005")
def test_report_subcommand_routes_to_command_report():
    with (
        patch.object(Command, "command_report") as mock_report,
        patch("sys.argv", ["reqstool", "report", "--format", "asciidoc", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_report.assert_called_once()


@SVCs("SVC_REPORT_0006")
def test_report_asciidoc_deprecated_warning_printed_to_stderr(capsys):
    with (
        patch.object(Command, "command_report"),
        patch("sys.argv", ["reqstool", "report-asciidoc", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
        assert "report-asciidoc" in captured.err


def test_report_asciidoc_still_calls_command_report():
    with (
        patch.object(Command, "command_report") as mock_report,
        patch("sys.argv", ["reqstool", "report-asciidoc", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_report.assert_called_once()


@SVCs("SVC_EXPORT_0005")
def test_export_subcommand_routes_to_command_export():
    with (
        patch.object(Command, "command_export") as mock_export,
        patch("sys.argv", ["reqstool", "export", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_export.assert_called_once()


def test_validate_subcommand_routes_to_command_validate():
    with (
        patch.object(Command, "command_validate", return_value=0) as mock_validate,
        patch("sys.argv", ["reqstool", "validate", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_validate.assert_called_once()


def test_status_subcommand_routes_to_command_status():
    with (
        patch.object(Command, "command_status", return_value=0) as mock_status,
        patch("sys.argv", ["reqstool", "status", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_status.assert_called_once()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


def test_missing_requirements_error_exits_with_correct_code():
    with (
        patch.object(Command, "command_report", side_effect=MissingRequirementsFileError("/fake")),
        patch("sys.argv", ["reqstool", "report", "local", "-p", "/tmp"]),
        patch("sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_any_call(EXIT_CODE_MISSING_REQUIREMENTS_FILE)


@SVCs("SVC_STATUS_0007")
def test_status_nonzero_exit_code_is_propagated():
    with (
        patch.object(Command, "command_status", return_value=EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED),
        patch(
            "sys.argv",
            ["reqstool", "status", "--check-all-reqs-met", "local", "-p", "/tmp"],
        ),
        patch("sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_called_with(EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED)


# ---------------------------------------------------------------------------
# Argument parsing tests
# ---------------------------------------------------------------------------


def _make_command_and_parse(argv):
    """Helper: instantiate Command and parse the given argv list."""
    cmd = Command()
    with patch("sys.argv", argv):
        return cmd.get_arguments()


def test_local_source_parser_accepts_path_arg():
    args = _make_command_and_parse(["reqstool", "report", "local", "-p", "/some/path"])
    assert args.command == "report"
    assert args.source == "local"
    assert args.path == "/some/path"


def test_git_source_parser_requires_url_path_and_ref():
    args = _make_command_and_parse(
        ["reqstool", "report", "git", "-u", "https://example.com/repo", "-p", "docs/reqstool", "-r", "v1.0.0"]
    )
    assert args.command == "report"
    assert args.source == "git"
    assert args.url == "https://example.com/repo"
    assert args.path == "docs/reqstool"
    assert args.ref == "v1.0.0"


def test_git_source_parser_accepts_token():
    args = _make_command_and_parse(
        ["reqstool", "report", "git", "-u", "https://example.com/repo", "-p", "docs", "-r", "main", "-t", "secret"]
    )
    assert args.token == "secret"


def test_maven_source_parser_accepts_token():
    args = _make_command_and_parse(
        ["reqstool", "report", "maven", "--group_id", "com.ex", "--artifact_id", "lib", "--version", "1.0.0", "-t", "s"]
    )
    assert args.token == "s"


def test_pypi_source_parser_accepts_token():
    args = _make_command_and_parse(
        ["reqstool", "report", "pypi", "--package", "mypkg", "--version", "1.0.0", "-t", "secret"]
    )
    assert args.token == "secret"


def test_get_initial_source_git_with_token():
    args = argparse.Namespace(source="git", url="https://example.com/repo.git", path="docs", ref="main", token="sec")
    loc = Command()._get_initial_source(args)
    assert isinstance(loc, GitLocation)
    assert loc.token.get_secret_value() == "sec"


def test_get_initial_source_maven_with_token():
    args = argparse.Namespace(
        source="maven",
        url=None,
        group_id="com.example",
        artifact_id="lib",
        version="1.0.0",
        classifier="reqstool",
        token="sec",
    )
    loc = Command()._get_initial_source(args)
    assert isinstance(loc, MavenLocation)
    assert loc.token.get_secret_value() == "sec"


def test_get_initial_source_pypi_with_token():
    args = argparse.Namespace(
        source="pypi", url="https://pypi.org/simple", package="mypkg", version="1.0.0", token="sec"
    )
    loc = Command()._get_initial_source(args)
    assert isinstance(loc, PypiLocation)
    assert loc.token.get_secret_value() == "sec"


def test_git_source_parser_missing_ref_errors():
    with pytest.raises(SystemExit):
        _make_command_and_parse(["reqstool", "report", "git", "-u", "https://example.com/repo", "-p", "docs/reqstool"])


def test_maven_source_parser_requires_group_artifact_version():
    args = _make_command_and_parse(
        [
            "reqstool",
            "report",
            "maven",
            "--group_id",
            "com.example",
            "--artifact_id",
            "my-artifact",
            "--version",
            "1.0.0",
        ]
    )
    assert args.command == "report"
    assert args.source == "maven"
    assert args.group_id == "com.example"
    assert args.artifact_id == "my-artifact"
    assert args.version == "1.0.0"


def test_pypi_source_parser_requires_package_and_version():
    args = _make_command_and_parse(["reqstool", "report", "pypi", "--package", "my-package", "--version", "2.3.4"])
    assert args.command == "report"
    assert args.source == "pypi"
    assert args.package == "my-package"
    assert args.version == "2.3.4"


def test_npm_source_parser_requires_package_and_version():
    args = _make_command_and_parse(["reqstool", "report", "npm", "--package", "@scope/my-pkg", "--version", "1.2.3"])
    assert args.command == "report"
    assert args.source == "npm"
    assert args.package == "@scope/my-pkg"
    assert args.version == "1.2.3"


def test_npm_source_parser_accepts_custom_url_and_token():
    args = _make_command_and_parse(
        [
            "reqstool",
            "report",
            "npm",
            "--package",
            "my-pkg",
            "--version",
            "1.0.0",
            "--url",
            "https://my.registry.example.com",
            "--token",
            "NPM_TOKEN",
        ]
    )
    assert args.url == "https://my.registry.example.com"
    assert args.token == "NPM_TOKEN"


def test_local_source_parser_accepts_npm_path_arg():
    args = _make_command_and_parse(["reqstool", "report", "local", "--npm", "path/to/pkg.tgz"])
    assert args.source == "local"
    assert args.npm == "path/to/pkg.tgz"


def test_get_initial_source_npm_returns_npm_location():
    args = argparse.Namespace(source="npm", package="my-pkg-reqstool", version="1.0.0", url=None, token=None)
    loc = Command()._get_initial_source(args)
    assert isinstance(loc, NpmLocation)
    assert loc.package == "my-pkg-reqstool"
    assert loc.version == "1.0.0"
    assert loc.url == "https://registry.npmjs.org"


def test_get_initial_source_npm_with_custom_url():
    args = argparse.Namespace(
        source="npm",
        package="my-pkg-reqstool",
        version="1.0.0",
        url="https://my.registry.example.com",
        token="NPM_TOKEN",
    )
    loc = Command()._get_initial_source(args)
    assert isinstance(loc, NpmLocation)
    assert loc.url == "https://my.registry.example.com"
    assert loc.token.get_secret_value() == "NPM_TOKEN"


def test_get_initial_source_local_npm_returns_local_npm_location():
    args = argparse.Namespace(source="local", npm="path/to/pkg.tgz", maven=None, pypi=None, path=None)
    loc = Command()._get_initial_source(args)
    assert isinstance(loc, LocalNpmLocation)
    assert loc.path == "path/to/pkg.tgz"


def test_artifact_download_error_exits_with_correct_code():
    with (
        patch.object(Command, "command_report", side_effect=ArtifactDownloadError("download failed")),
        patch("sys.argv", ["reqstool", "report", "local", "-p", "/tmp"]),
        patch("sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_any_call(EXIT_CODE_ARTIFACT_ERROR)


def test_mcp_parses_without_source():
    args = _make_command_and_parse(["reqstool", "mcp"])
    assert args.command == "mcp"
    assert args.source is None


def test_mcp_still_accepts_local_source():
    args = _make_command_and_parse(["reqstool", "mcp", "local", "-p", "/some/path"])
    assert args.command == "mcp"
    assert args.source == "local"
    assert args.path == "/some/path"


def test_status_with_post_tests_single_path():
    args = _make_command_and_parse(["reqstool", "status", "--with-post-tests", "/tmp/e2e.xml", "local", "-p", "/tmp"])
    assert args.command == "status"
    assert args.with_post_tests == ["/tmp/e2e.xml"]


def test_status_with_post_tests_multiple_paths():
    args = _make_command_and_parse(
        [
            "reqstool",
            "status",
            "--with-post-tests",
            "/tmp/e2e1.xml",
            "--with-post-tests",
            "/tmp/e2e2.xml",
            "local",
            "-p",
            "/tmp",
        ]
    )
    assert args.with_post_tests == ["/tmp/e2e1.xml", "/tmp/e2e2.xml"]


def test_status_without_post_tests_defaults_to_none():
    args = _make_command_and_parse(["reqstool", "status", "local", "-p", "/tmp"])
    assert args.with_post_tests is None


# ---------------------------------------------------------------------------
# LSP / MCP server option + dependency-guard tests
# ---------------------------------------------------------------------------


@SVCs("SVC_LSP_0002")
def test_lsp_tcp_transport_args_parsed():
    args = _make_command_and_parse(["reqstool", "lsp", "--tcp", "--host", "0.0.0.0", "--port", "9999"])
    assert args.tcp is True
    assert args.host == "0.0.0.0"
    assert args.port == 9999


def test_lsp_log_file_arg_parsed():
    args = _make_command_and_parse(["reqstool", "lsp", "--log-file", "/tmp/lsp.log"])
    assert args.log_file == "/tmp/lsp.log"


@SVCs("SVC_LSP_0003")
def test_lsp_log_file_passed_to_server():
    """LSP_0003: the configured log-file path is forwarded to the language server."""
    cmd = Command()
    lsp_args = argparse.Namespace(tcp=False, host="127.0.0.1", port=2087, log_file="/tmp/lsp.log")
    fake_server = MagicMock()
    with patch.dict(sys.modules, {"reqstool.lsp.server": MagicMock(start_server=fake_server.start_server)}):
        cmd.command_lsp(lsp_args)
    assert fake_server.start_server.call_args.kwargs["log_file"] == "/tmp/lsp.log"


@SVCs("SVC_LSP_0004")
def test_lsp_missing_extra_reports_and_exits(capsys):
    cmd = Command()
    lsp_args = argparse.Namespace(tcp=False, host="127.0.0.1", port=2087, log_file=None)
    with patch.dict(sys.modules, {"reqstool.lsp.server": None}):
        with pytest.raises(SystemExit) as exc:
            cmd.command_lsp(lsp_args)
    assert exc.value.code == 1
    assert "pip install reqstool[lsp]" in capsys.readouterr().err


@SVCs("SVC_MCP_0002")
def test_mcp_transport_args_parsed():
    args = _make_command_and_parse(["reqstool", "mcp", "--transport", "sse", "--host", "h", "--port", "1234"])
    assert args.transport == "sse"
    assert args.host == "h"
    assert args.port == 1234


@SVCs("SVC_MCP_0004")
def test_mcp_missing_extra_reports_and_exits(capsys):
    cmd = Command()
    mcp_args = argparse.Namespace(
        source="local", path="/tmp", transport="stdio", host="127.0.0.1", port=8000, maven=None, npm=None, pypi=None
    )
    with patch.dict(sys.modules, {"reqstool.mcp.server": None}):
        with pytest.raises(SystemExit) as exc:
            cmd.command_mcp(mcp_args)
    assert exc.value.code == 1
    assert "pip install 'mcp>=1.0'" in capsys.readouterr().err


@SVCs("SVC_MCP_0003")
def test_mcp_auto_detects_dataset_from_config():
    """MCP_0003: with no explicit source, the dataset is resolved from the reqstool AI config file."""
    cmd = Command()
    mcp_args = argparse.Namespace(source=None, transport="stdio", host="127.0.0.1", port=8000)
    mock_server = MagicMock()
    with (
        patch.dict(sys.modules, {"reqstool.mcp.server": mock_server}),
        patch("reqstool.common.reqstool_ai_config.find_config", return_value="/proj/.reqstool-ai.yaml"),
        patch("reqstool.common.reqstool_ai_config.resolve_system_path", return_value="/proj/docs/reqstool"),
    ):
        cmd.command_mcp(mcp_args)
    location = mock_server.start_server.call_args.kwargs["location"]
    assert location.path == "/proj/docs/reqstool"


@SVCs("SVC_MCP_0003")
def test_mcp_no_source_no_config_exits(capsys):
    """MCP_0003: with neither an explicit source nor a config file, the command errors out."""
    cmd = Command()
    mcp_args = argparse.Namespace(source=None, transport="stdio", host="127.0.0.1", port=8000)
    with (
        patch.dict(sys.modules, {"reqstool.mcp.server": MagicMock()}),
        patch("reqstool.common.reqstool_ai_config.find_config", return_value=None),
    ):
        with pytest.raises(SystemExit) as exc:
            cmd.command_mcp(mcp_args)
    assert exc.value.code == 2
    assert "reqstool mcp:" in capsys.readouterr().err


@SVCs("SVC_STATUS_0009")
def test_command_status_writes_result_to_output_destination():
    """STATUS_0009: status content is written to the provided output handle rather than only stdout."""
    out = io.StringIO()
    # command_status reads only output and check_all_reqs_met directly (everything else goes
    # through getattr defaults or the mocked StatusCommand / _get_initial_source).
    args = argparse.Namespace(output=out, check_all_reqs_met=False)
    with (
        patch.object(Command, "_get_initial_source", return_value=MagicMock()),
        patch("reqstool.command.StatusCommand") as mock_status,
    ):
        mock_status.return_value.result = ("STATUS-BODY", 0)
        exit_code = Command().command_status(args)
    assert out.getvalue() == "STATUS-BODY"
    assert exit_code == 0


@SVCs("SVC_STATUS_0007")
def test_command_status_returns_nonzero_when_enforcing_and_incomplete():
    """STATUS_0007: with --check-all-reqs-met and incomplete requirements, exit with the
    all-requirements-not-implemented code; the same incomplete result exits zero otherwise."""
    out = io.StringIO()
    args = argparse.Namespace(output=out, check_all_reqs_met=True)
    with (
        patch.object(Command, "_get_initial_source", return_value=MagicMock()),
        patch("reqstool.command.StatusCommand") as mock_status,
    ):
        mock_status.return_value.result = ("STATUS-BODY", 2)
        exit_code = Command().command_status(args)
    assert exit_code == EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED

    out = io.StringIO()
    args = argparse.Namespace(output=out, check_all_reqs_met=False)
    with (
        patch.object(Command, "_get_initial_source", return_value=MagicMock()),
        patch("reqstool.command.StatusCommand") as mock_status,
    ):
        mock_status.return_value.result = ("STATUS-BODY", 2)
        exit_code = Command().command_status(args)
    assert exit_code == 0
