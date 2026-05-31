#!/usr/bin/env python3
# Copyright © LFV

import argparse
import logging
import os
import sys
from typing import Literal, Optional, TextIO, Union, cast

if __package__ is None or len(__package__) == 0:
    _script_dir = os.path.abspath(os.path.dirname(__file__))
    # Remove the script directory from sys.path: Python adds it automatically, but
    # reqstool subpackages (e.g. mcp/) would then shadow same-named third-party packages.
    if _script_dir in sys.path:
        sys.path.remove(_script_dir)
    sys.path.insert(0, os.path.abspath(os.path.join(_script_dir, "..")))

    from reqstool.common.utils import Utils

    Utils.is_installed_package = False


from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.commands.exit_codes import (
    EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED,
    EXIT_CODE_ARTIFACT_ERROR,
    EXIT_CODE_MISSING_REQUIREMENTS_FILE,
)
from reqstool.common.exceptions import ArtifactDownloadError, ArtifactExtractionError, MissingRequirementsFileError
from reqstool.commands.generate_json.generate_json import GenerateJsonCommand
from reqstool.commands.report import report
from reqstool.commands.validate.validate import ValidateCommand
from reqstool.commands.report.criterias.group_by import GroupbyOptions
from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.commands.enrich.enrich import EnrichCommand
from reqstool.commands.status.status import StatusCommand, VerbosityLevel
from reqstool.common.enrichment.enricher import BUILT_IN_PRESETS
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaItem
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.local_maven_location import LocalMavenLocation
from reqstool.locations.local_npm_location import LocalNpmLocation
from reqstool.locations.local_pypi_location import LocalPypiLocation
from reqstool.locations.location import LocationInterface
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.npm_location import NpmLocation
from reqstool.locations.pypi_location import PypiLocation


_LOCATION_DEFS = [
    {
        "name": "local",
        "help": "local source",
        "exclusive_group": True,
        "args": [
            {"flags": ["-p", "--path"], "kwargs": {"help": "path to a local directory"}},
            {"flags": ["--maven"], "kwargs": {"metavar": "PATH", "help": "path to a local Maven ZIP artifact (.zip)"}},
            {
                "flags": ["--npm"],
                "kwargs": {"metavar": "PATH", "help": "path to a local npm tarball (.tgz)"},
            },
            {
                "flags": ["--pypi"],
                "kwargs": {"metavar": "PATH", "help": "path to a local PyPI sdist tarball (.tar.gz)"},
            },
        ],
    },
    {
        "name": "git",
        "help": "git source",
        "args": [
            {"flags": ["-u", "--url"], "kwargs": {"help": "git repository URL", "required": True}},
            {"flags": ["-p", "--path"], "kwargs": {"help": "path within the repository", "required": True}},
            {"flags": ["-r", "--ref"], "kwargs": {"help": "git branch, tag, or commit SHA", "required": True}},
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env var name holding the access token"}},
        ],
    },
    {
        "name": "maven",
        "help": "maven source",
        "args": [
            {"flags": ["-u", "--url"], "kwargs": {"help": "Maven repository URL", "required": False}},
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env var name holding the access token"}},
            {"flags": ["--group_id"], "kwargs": {"help": "Maven group ID", "required": True}},
            {"flags": ["--artifact_id"], "kwargs": {"help": "Maven artifact ID", "required": True}},
            {"flags": ["--version"], "kwargs": {"help": "artifact version (e.g. 1.2.3)", "required": True}},
            {"flags": ["--classifier"], "kwargs": {"help": "Maven classifier"}},
        ],
    },
    {
        "name": "npm",
        "help": "npm source",
        "args": [
            {
                "flags": ["-u", "--url"],
                "kwargs": {
                    "help": "npm-compatible registry URL (default: https://registry.npmjs.org)",
                    "required": False,
                },
            },
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env var name holding the Bearer token"}},
            {"flags": ["--package"], "kwargs": {"help": "npm package name (e.g. @scope/package)", "required": True}},
            {"flags": ["--version"], "kwargs": {"help": "package version (e.g. 1.2.3)", "required": True}},
        ],
    },
    {
        "name": "pypi",
        "help": "pypi source",
        "args": [
            {"flags": ["-u", "--url"], "kwargs": {"help": "PyPI index URL", "required": False}},
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env var name holding the access token"}},
            {"flags": ["--package"], "kwargs": {"help": "PyPI package name", "required": True}},
            {"flags": ["--version"], "kwargs": {"help": "package version (e.g. 1.2.3)", "required": True}},
        ],
    },
]


class Command:
    __parser: argparse.Namespace

    @staticmethod
    def create_directory_and_open(file_path: Union[TextIO, str]) -> TextIO:
        """
        Create the directory if it doesn't exist and open the specified file.

        If file_path is sys.stdout it is returned as-is; otherwise a new writable
        file handle is opened at the given path (directories are created as needed).
        """
        if file_path is sys.stdout:
            return sys.stdout  # type: ignore[return-value]

        assert isinstance(file_path, str)
        directory = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(directory, exist_ok=True)
        return open(file_path, "w")

    def _add_argument_output(self, argument_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        argument_parser.add_argument(
            "-o",
            "--output",
            nargs="?",
            help="Where to output result (default: stdout)",
            type=lambda file: Command.create_directory_and_open(file),
            default=sys.stdout,
        )
        return argument_parser

    def _add_group_by(self, argument_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        argument_parser.add_argument(
            "--group-by",
            type=str,
            help="Grouping option (default: %(default)s)",
            choices=[c.value for c in GroupbyOptions],
            default=GroupbyOptions.INITIAL_IMPORTS.value,
        )
        return argument_parser

    def _add_sort_by(self, argument_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        argument_parser.add_argument(
            "--sort-by",
            type=str,
            nargs="+",
            choices=[s.value for s in SortByOptions],
            help="List of sorting options (default: %(default)s)",
            default=[SortByOptions.ID.value],
        )
        return argument_parser

    def _add_filter_options(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--req-ids",
            "--requirement-ids",
            nargs="+",
            dest="req_ids",
            help=(
                "Filter output to specific requirement IDs "
                "(e.g. REQ_010 or ms-001:REQ_010; must follow the location subcommand, "
                "e.g. local -p . --req-ids REQ_010)"
            ),
            default=None,
        )
        parser.add_argument(
            "--svc-ids",
            nargs="+",
            dest="svc_ids",
            help=(
                "Filter output to specific SVC IDs "
                "(e.g. SVC_010 or ms-001:SVC_010; must follow the location subcommand)"
            ),
            default=None,
        )

    def _add_subparsers_source(self, parser, include_report_options=True, include_filter_options=False):
        for loc in _LOCATION_DEFS:
            sub = parser.add_parser(loc["name"], help=loc["help"])
            if loc.get("exclusive_group"):
                grp = sub.add_mutually_exclusive_group(required=True)
                for arg in loc["args"]:
                    grp.add_argument(*arg["flags"], **arg["kwargs"])
            else:
                for arg in loc["args"]:
                    sub.add_argument(*arg["flags"], **arg["kwargs"])
            self._add_argument_output(sub)
            if include_report_options:
                self._add_group_by(sub)
                self._add_sort_by(sub)
            if include_filter_options:
                self._add_filter_options(sub)

    def _add_argument_version(self, argument_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        ver = Utils.get_version()

        argument_parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"""
{ver}
        # JSON Schema version: {JsonSchemaItem.schema_version}
        # JSON Schema location: {JsonSchemaItem.schema_module.__path__._path[0]}""",
        )

        return argument_parser

    def _add_argument_log_level(self, argument_parser: argparse.ArgumentParser) -> None:
        argument_parser.add_argument(
            "--log", default="WARNING", help="Set the logging level (FATAL, ERROR, WARNING, INFO, DEBUG)."
        )

    def get_arguments(self) -> argparse.Namespace:
        class ComboRawTextandArgsDefaultUltimateHelpFormatter(
            argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
        ):
            pass

        self.__parser = argparse.ArgumentParser(
            description="reqstool - the command line utility for Reqstool",
            formatter_class=ComboRawTextandArgsDefaultUltimateHelpFormatter,
        )

        self._add_argument_version(self.__parser)
        self._add_argument_log_level(self.__parser)

        subparsers = self.__parser.add_subparsers(dest="command", help="Sub-commands")

        # command: report
        report_parser = subparsers.add_parser("report", help="Generate a report")
        report_parser.add_argument(
            "--format",
            choices=["asciidoc", "markdown"],
            default="asciidoc",
            help="Output format (default: %(default)s)",
        )
        report_source_subparsers = report_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(report_source_subparsers)

        # command: report-asciidoc (deprecated, use 'report' instead)
        report_asciidoc_parser = subparsers.add_parser(
            "report-asciidoc", help="[DEPRECATED: use 'report --format asciidoc'] Generate a report in AsciiDoc"
        )
        report_asciidoc_source_subparsers = report_asciidoc_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(report_asciidoc_source_subparsers)

        # command: export
        export_parser = subparsers.add_parser("export", help="Export data in specified format")

        export_parser.add_argument(
            "--format",
            choices=["json", "sqlite"],
            default="json",
            help="Output format (sqlite requires -o <file>)",
        )

        export_parser.add_argument(
            "--no-filters",
            action="store_true",
            help="Do not filter data",
            default=False,
            required=False,
        )

        export_source_subparsers = export_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(export_source_subparsers, include_report_options=False, include_filter_options=True)

        # command: validate
        validate_parser = subparsers.add_parser(
            "validate", help="Validate spec completeness (every requirement has SVCs, manual SVCs have MVRs)"
        )
        validate_parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat coverage warnings as errors (fail if any coverage gap)",
            default=False,
        )
        validate_source_subparsers = validate_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(validate_source_subparsers, include_report_options=False)

        # command: status
        status_parser = subparsers.add_parser("status", help="Status on implementations and tests of requirements")
        status_parser.add_argument(
            "--format",
            choices=["console", "json"],
            default="console",
            help="Output format (default: %(default)s)",
        )
        status_parser.add_argument(
            "--verbosity",
            choices=[v.value for v in VerbosityLevel],
            default=VerbosityLevel.NORMAL.value,
            help="Console output detail level (default: %(default)s; ignored for --format json)",
        )
        status_parser.add_argument(
            "--incomplete",
            action="store_true",
            default=False,
            help="Show only incomplete requirements",
        )
        status_parser.add_argument(
            "--check-all-reqs-met",
            action="store_true",
            help="Fail unless all requirements are implemented",
        )
        status_source_subparsers = status_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(status_source_subparsers, include_report_options=False, include_filter_options=True)

        # command: enrich
        enrich_parser = subparsers.add_parser(
            "enrich",
            help=(
                "Enrich a document with requirement/SVC/MVR titles and descriptions. "
                "Auto-detects dataset from .reqstool-ai.yaml if no source is given."
            ),
        )
        enrich_parser.add_argument(
            "--preset",
            required=True,
            choices=sorted(BUILT_IN_PRESETS),
            help="Enrichment preset (e.g. openspec:spec, openspec:design)",
        )
        enrich_parser.add_argument(
            "--input",
            "-i",
            metavar="FILE",
            default=None,
            help="Input file to enrich (default: stdin)",
        )
        self._add_argument_output(enrich_parser)
        enrich_source_subparsers = enrich_parser.add_subparsers(dest="source", required=False)
        self._add_subparsers_source(
            enrich_source_subparsers, include_report_options=False, include_filter_options=False
        )

        # command: lsp
        lsp_parser = subparsers.add_parser(
            "lsp", help="Start the Language Server Protocol server (requires reqstool[lsp])"
        )
        lsp_parser.add_argument(
            "--stdio",
            action="store_true",
            default=True,
            help="Use stdio transport (default)",
        )
        lsp_parser.add_argument(
            "--tcp",
            action="store_true",
            default=False,
            help="Use TCP transport instead of stdio",
        )
        lsp_parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="TCP host (default: %(default)s)",
        )
        lsp_parser.add_argument(
            "--port",
            type=int,
            default=2087,
            help="TCP port (default: %(default)s)",
        )
        lsp_parser.add_argument(
            "--log-file",
            metavar="PATH",
            default=None,
            help="Write server logs to a file (in addition to stderr)",
        )

        # command: mcp
        mcp_parser = subparsers.add_parser(
            "mcp",
            help=(
                "Start the Model Context Protocol server. "
                "With no source, auto-detects the dataset from .reqstool-ai.yaml in cwd or an ancestor directory."
            ),
        )
        mcp_parser.add_argument(
            "--transport",
            choices=["stdio", "sse", "streamable-http"],
            default="stdio",
            help="Transport to use (default: %(default)s)",
        )
        mcp_parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host for HTTP transports (default: %(default)s)",
        )
        mcp_parser.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Port for HTTP transports (default: %(default)s)",
        )
        mcp_source_subparsers = mcp_parser.add_subparsers(dest="source", required=False)
        self._add_subparsers_source(mcp_source_subparsers, include_report_options=False, include_filter_options=False)

        args = self.__parser.parse_args()

        return args

    def _get_initial_source(self, args_source: argparse.Namespace) -> LocationInterface:
        location: Optional[LocationInterface] = None

        if args_source.source == "maven":
            location = MavenLocation(
                url=args_source.url if args_source.url else None,
                group_id=args_source.group_id,
                artifact_id=args_source.artifact_id,
                version=args_source.version,
                classifier=args_source.classifier if args_source.classifier else None,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif args_source.source == "npm":
            location = NpmLocation(
                url=args_source.url if args_source.url else "https://registry.npmjs.org",
                package=args_source.package,
                version=args_source.version,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif args_source.source == "pypi":
            location = PypiLocation(
                url=args_source.url if args_source.url else None,
                package=args_source.package,
                version=args_source.version,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif args_source.source == "git":
            location = GitLocation(
                url=args_source.url,
                path=args_source.path,
                ref=args_source.ref,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif args_source.source == "local":
            if args_source.maven:
                location = LocalMavenLocation(path=args_source.maven)
            elif args_source.npm:
                location = LocalNpmLocation(path=args_source.npm)
            elif args_source.pypi:
                location = LocalPypiLocation(path=args_source.pypi)
            else:
                location = LocalLocation(path=args_source.path)

        return location

    @Requirements("REQ_035")
    def command_report(self, report_args: argparse.Namespace):
        initial_source = self._get_initial_source(report_args)

        output = report_args.output  # where to put the generated report
        format = getattr(report_args, "format", "asciidoc")
        result = report.ReportCommand(
            location=initial_source,
            group_by=GroupbyOptions(report_args.group_by),
            sort_by=[SortByOptions(s) for s in report_args.sort_by],
            format=format,
        )

        output.write(result.result)

    def command_export(self, export_args: argparse.Namespace):
        initial_source = self._get_initial_source(export_args)
        fmt = getattr(export_args, "format", "json")

        if fmt == "sqlite":
            output = export_args.output
            if output is sys.stdout:
                print("Error: --format sqlite requires -o <file>", file=sys.stderr)
                sys.exit(1)
            output_path = output.name
            output.close()
            from reqstool.common.validator_error_holder import ValidationErrorHolder
            from reqstool.common.validators.semantic_validator import SemanticValidator
            from reqstool.storage.pipeline import build_database

            filter_data = not getattr(export_args, "no_filters", False)
            with build_database(
                location=initial_source,
                semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
                filter_data=filter_data,
            ) as (db, _):
                db.backup_to(output_path)
        else:
            filter_data = not getattr(export_args, "no_filters", False)
            req_ids = getattr(export_args, "req_ids", None)
            svc_ids = getattr(export_args, "svc_ids", None)
            result = GenerateJsonCommand(
                location=initial_source, filter_data=filter_data, req_ids=req_ids, svc_ids=svc_ids
            )
            export_args.output.write(result.result)

    def command_validate(self, validate_args: argparse.Namespace) -> int:
        initial_source = self._get_initial_source(validate_args)
        output = validate_args.output
        strict = getattr(validate_args, "strict", False)

        result = ValidateCommand(location=initial_source, strict=strict)
        output.write(result.result)
        return result.exit_code

    @Requirements("REQ_029")
    def command_status(self, status_args: argparse.Namespace) -> int:
        initial_source = self._get_initial_source(status_args)
        output = status_args.output

        fmt = getattr(status_args, "format", "console")
        verbosity = getattr(status_args, "verbosity", VerbosityLevel.NORMAL.value)
        incomplete_only = getattr(status_args, "incomplete", False)
        req_ids = getattr(status_args, "req_ids", None)
        svc_ids = getattr(status_args, "svc_ids", None)

        result = StatusCommand(
            location=initial_source,
            format=fmt,
            verbosity=verbosity,
            incomplete_only=incomplete_only,
            req_ids=req_ids,
            svc_ids=svc_ids,
        )
        status, nr_of_incomplete_requirements = result.result

        output.write(str(status))

        return (
            EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED
            if status_args.check_all_reqs_met and nr_of_incomplete_requirements > 0
            else 0
        )

    def command_lsp(self, lsp_args: argparse.Namespace):
        try:
            from reqstool.lsp.server import start_server
        except ImportError:
            print(
                "LSP server requires extra dependencies: pip install reqstool[lsp]",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            start_server(tcp=lsp_args.tcp, host=lsp_args.host, port=lsp_args.port, log_file=lsp_args.log_file)
        except Exception as exc:
            logging.fatal("reqstool LSP server crashed: %s", exc)
            sys.exit(1)

    def command_mcp(self, mcp_args: argparse.Namespace):
        try:
            from reqstool.mcp.server import start_server
        except ImportError:
            print(
                "MCP server requires extra dependencies: pip install 'mcp>=1.0'",
                file=sys.stderr,
            )
            sys.exit(1)

        if getattr(mcp_args, "source", None) is None:
            from pathlib import Path

            from reqstool.common.reqstool_ai_config import CONFIG_FILENAME, find_config, resolve_system_path

            config_path = find_config()
            if config_path is None:
                print(
                    f"reqstool mcp: no {CONFIG_FILENAME} found from {Path.cwd()} upward; "
                    f"either run from a project containing {CONFIG_FILENAME} or specify an explicit source "
                    f"(e.g. `reqstool mcp local -p <path>`).",
                    file=sys.stderr,
                )
                sys.exit(2)
            try:
                resolved = resolve_system_path(config_path)
            except ValueError as exc:
                print(f"reqstool mcp: {exc}", file=sys.stderr)
                sys.exit(2)
            location: LocationInterface = LocalLocation(path=str(resolved))
        else:
            location = self._get_initial_source(mcp_args)

        try:
            start_server(
                location=location,
                transport=cast(Literal["stdio", "sse", "streamable-http"], mcp_args.transport),
                host=mcp_args.host,
                port=mcp_args.port,
            )
        except Exception as exc:
            logging.fatal("reqstool MCP server crashed: %s", exc)
            sys.exit(1)

    @Requirements("REQ_039")
    def command_enrich(self, enrich_args: argparse.Namespace):
        if getattr(enrich_args, "source", None) is None:
            from pathlib import Path

            from reqstool.common.reqstool_ai_config import CONFIG_FILENAME, find_config, resolve_system_path

            config_path = find_config()
            if config_path is None:
                print(
                    f"reqstool enrich: no {CONFIG_FILENAME} found from {Path.cwd()} upward; "
                    f"either run from a project containing {CONFIG_FILENAME} or specify an explicit source "
                    f"(e.g. `reqstool enrich --preset openspec:spec --input foo.md local -p <path>`).",
                    file=sys.stderr,
                )
                sys.exit(2)
            try:
                resolved = resolve_system_path(config_path)
            except ValueError as exc:
                print(f"reqstool enrich: {exc}", file=sys.stderr)
                sys.exit(2)
            location: LocationInterface = LocalLocation(path=str(resolved))
        else:
            location = self._get_initial_source(enrich_args)

        input_file = getattr(enrich_args, "input", None)
        if input_file is None:
            input_content = sys.stdin.read()
        else:
            with open(input_file, encoding="utf-8") as f:
                input_content = f.read()

        config = BUILT_IN_PRESETS[enrich_args.preset]
        result = EnrichCommand(location=location, input_content=input_content, config=config)
        enrich_args.output.write(result.result)

    def print_help(self):
        self.__parser.print_help(sys.stderr)


def main():  # noqa: C901
    command = Command()
    args = command.get_arguments()

    # Set the logging level based on the argument
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.WARNING))

    exit_code: int = 0

    try:
        if args.command == "report":
            command.command_report(report_args=args)
        elif args.command == "report-asciidoc":
            print(
                "WARNING: 'report-asciidoc' is deprecated. Use 'report --format asciidoc' instead.",
                file=sys.stderr,
            )
            command.command_report(report_args=args)
        elif args.command == "export":
            command.command_export(export_args=args)
        elif args.command == "validate":
            exit_code = command.command_validate(validate_args=args)
        elif args.command == "status":
            exit_code = command.command_status(status_args=args)
        elif args.command == "lsp":
            command.command_lsp(lsp_args=args)
        elif args.command == "mcp":
            command.command_mcp(mcp_args=args)
        elif args.command == "enrich":
            command.command_enrich(enrich_args=args)
        else:
            command.print_help()
    except MissingRequirementsFileError as exc:
        logging.fatal(str(exc))
        sys.exit(EXIT_CODE_MISSING_REQUIREMENTS_FILE)
    except (ArtifactDownloadError, ArtifactExtractionError) as exc:
        logging.fatal(str(exc))
        sys.exit(EXIT_CODE_ARTIFACT_ERROR)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
