# Copyright © LFV

from unittest.mock import patch

import pytest

from reqstool.command import Command, main
from reqstool.commands.exit_codes import EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED, EXIT_CODE_MISSING_REQUIREMENTS_FILE
from reqstool.common.exceptions import MissingRequirementsFileError


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


def test_report_subcommand_routes_to_command_report():
    with (
        patch.object(Command, "command_report") as mock_report,
        patch("sys.argv", ["reqstool", "report", "--format", "asciidoc", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_report.assert_called_once()


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


def test_export_subcommand_routes_to_command_export():
    with (
        patch.object(Command, "command_export") as mock_export,
        patch("sys.argv", ["reqstool", "export", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_export.assert_called_once()


def test_generate_json_deprecated_warning_printed_to_stderr(capsys):
    with (
        patch.object(Command, "command_generate_json"),
        patch("sys.argv", ["reqstool", "generate-json", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
        assert "generate-json" in captured.err


def test_generate_json_still_calls_command_generate_json():
    with (
        patch.object(Command, "command_generate_json") as mock_gen,
        patch("sys.argv", ["reqstool", "generate-json", "local", "-p", "/tmp"]),
        patch("sys.exit"),
    ):
        main()
        mock_gen.assert_called_once()


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
