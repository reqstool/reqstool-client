#!/usr/bin/env python3
# Copyright © LFV

import argparse
import logging
import os
import sys
from typing import Optional, TextIO, Union

if __package__ is None or len(__package__) == 0:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
from reqstool.commands.report.criterias.group_by import GroupbyOptions
from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.commands.status.status import StatusCommand
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaItem
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.local_maven_location import LocalMavenLocation
from reqstool.locations.local_pypi_location import LocalPypiLocation
from reqstool.locations.location import LocationInterface
from reqstool.locations.maven_location import MavenLocation
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
                "flags": ["--pypi"],
                "kwargs": {"metavar": "PATH", "help": "path to a local PyPI sdist tarball (.tar.gz)"},
            },
        ],
    },
    {
        "name": "git",
        "help": "git source",
        "args": [
            {"flags": ["-u", "--url"], "kwargs": {"help": "url description", "required": True}},
            {"flags": ["-p", "--path"], "kwargs": {"help": "path description", "required": True}},
            {"flags": ["-b", "--branch"], "kwargs": {"help": "branch description"}},
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env_token description"}},
        ],
    },
    {
        "name": "maven",
        "help": "maven source",
        "args": [
            {"flags": ["-u", "--url"], "kwargs": {"help": "url description", "required": False}},
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env_token description"}},
            {"flags": ["--group_id"], "kwargs": {"help": "group_id description", "required": True}},
            {"flags": ["--artifact_id"], "kwargs": {"help": "artifact_id description", "required": True}},
            {"flags": ["--version"], "kwargs": {"help": "version description", "required": True}},
            {"flags": ["--classifier"], "kwargs": {"help": "classifier description"}},
        ],
    },
    {
        "name": "pypi",
        "help": "pypi source",
        "args": [
            {"flags": ["-u", "--url"], "kwargs": {"help": "url description", "required": False}},
            {"flags": ["-t", "--env_token"], "kwargs": {"help": "env_token description"}},
            {"flags": ["--package"], "kwargs": {"help": "package", "required": True}},
            {"flags": ["--version"], "kwargs": {"help": "version description", "required": True}},
        ],
    },
]


class Command:
    __parser: argparse.Namespace

    @staticmethod
    def create_directory_and_open(file_path: Union[TextIO, str]) -> TextIO:
        """
        Create the directory if it doesn't exist and open the specified file.

        Parameters:
        - file_path (TextIO (sys.stdout) or str (path as argument on command line): The file path.
        - mode (str): The mode in which the file should be opened.

        Returns:
        - TextIO: The opened file.

        If the file path is sys.stdout, it is returned as is without attempting to create the directory.
        """
        if file_path == sys.stdout:
            return file_path

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
            help="Filter output to specific requirement IDs (e.g. REQ_010 or ms-001:REQ_010)",
            default=None,
        )
        parser.add_argument(
            "--svc-ids",
            nargs="+",
            dest="svc_ids",
            help="Filter output to specific SVC IDs (e.g. SVC_010 or ms-001:SVC_010)",
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

    def _add_argument_log_level(self, argument_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
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
            choices=["json"],
            default="json",
            help="Output format",
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

        # command: generate-json (deprecated, use 'export' instead)
        generate_json_parser = subparsers.add_parser(
            "generate-json", help="[DEPRECATED: use 'export --format json'] Export JSON"
        )

        generate_json_parser.add_argument(
            "--no-filter",
            action="store_true",
            dest="no_filters",
            help="Do not filter data",
            default=False,
            required=False,
        )

        generate_json_source_subparsers = generate_json_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(generate_json_source_subparsers, include_report_options=False)

        # command: status
        status_parser = subparsers.add_parser("status", help="Status on implementations and tests of requirements")
        status_parser.add_argument(
            "--format",
            choices=["console", "json"],
            default="console",
            help="Output format (default: %(default)s)",
        )
        status_parser.add_argument(
            "--check-all-reqs-met",
            action="store_true",
            help="Fail unless all requirements are implemented",
        )
        status_source_subparsers = status_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(status_source_subparsers)

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
        mcp_parser = subparsers.add_parser("mcp", help="Start the Model Context Protocol server (stdio)")
        mcp_source_subparsers = mcp_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(mcp_source_subparsers, include_report_options=False, include_filter_options=False)

        args = self.__parser.parse_args()

        return args

    def _get_initial_source(self, args_source: argparse.Namespace) -> LocationInterface:
        location: Optional[LocationInterface] = None

        if "maven" in args_source.source:
            location = MavenLocation(
                url=args_source.url if args_source.url else None,
                group_id=args_source.group_id,
                artifact_id=args_source.artifact_id,
                version=args_source.version,
                classifier=args_source.classifier if args_source.classifier else None,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif "pypi" in args_source.source:  # TODO $$$
            location = PypiLocation(
                url=args_source.url if args_source.url else None,
                package=args_source.package,
                version=args_source.version,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif "git" in args_source.source:
            location = GitLocation(
                url=args_source.url,
                path=args_source.path,
                branch=args_source.branch if args_source.branch else None,
                env_token=args_source.env_token if args_source.env_token else None,
            )
        elif "local" in args_source.source:
            if args_source.maven:
                location = LocalMavenLocation(path=args_source.maven)
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

        filter_data = not export_args.no_filters
        req_ids = getattr(export_args, "req_ids", None)
        svc_ids = getattr(export_args, "svc_ids", None)

        result = GenerateJsonCommand(location=initial_source, filter_data=filter_data, req_ids=req_ids, svc_ids=svc_ids)

        output = export_args.output
        output.write(result.result)

    @Requirements("REQ_031")
    def command_generate_json(self, generate_json_args: argparse.Namespace):
        initial_source = self._get_initial_source(generate_json_args)

        filter_data = not generate_json_args.no_filters

        result = GenerateJsonCommand(location=initial_source, filter_data=filter_data)

        output = generate_json_args.output  # where to put the generated report
        output.write(result.result)

    @Requirements("REQ_029")
    def command_status(self, status_args: argparse.Namespace) -> int:
        initial_source = self._get_initial_source(status_args)
        output = status_args.output  # where to put the generated report

        format = getattr(status_args, "format", "console")
        result = StatusCommand(location=initial_source, format=format)
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
        try:
            start_server(location=self._get_initial_source(mcp_args))
        except Exception as exc:
            logging.fatal("reqstool MCP server crashed: %s", exc)
            sys.exit(1)

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
        elif args.command == "generate-json":
            print(
                "WARNING: 'generate-json' is deprecated. Use 'export --format json' instead.",
                file=sys.stderr,
            )
            command.command_generate_json(generate_json_args=args)
        elif args.command == "status":
            exit_code = command.command_status(status_args=args)
        elif args.command == "lsp":
            command.command_lsp(lsp_args=args)
        elif args.command == "mcp":
            command.command_mcp(mcp_args=args)
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
