#!/usr/bin/env python3
# Copyright © LFV

import argparse
import logging
import os
import sys
from typing import TextIO, Union

if __package__ is None or len(__package__) == 0:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from reqstool.common.utils import Utils

    Utils.is_installed_package = False


from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.commands.exit_codes import EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED
from reqstool.commands.generate_json.generate_json import GenerateJsonCommand
from reqstool.commands.report import report
from reqstool.commands.report.criterias.group_by import GroupbyOptions
from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.commands.status.status import StatusCommand
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaItem

# from reqstool.common.validators.syntax_validator import JsonSchemaItem
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.location import LocationInterface
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.pypi_location import PypiLocation


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

        if not os.path.exists(directory):
            os.makedirs(directory)

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

    def _add_subparsers_source(self, parser, include_report_options=True):
        # Subparser for local report
        local_report_parser = parser.add_parser("local", help="local source")
        local_report_parser.add_argument("-p", "--path", help="path description", required=True)
        self._add_argument_output(local_report_parser)
        if include_report_options:
            self._add_group_by(local_report_parser)
            self._add_sort_by(local_report_parser)

        # Subparser for git report
        git_report_parser = parser.add_parser("git", help="git source")
        git_report_parser.add_argument("-u", "--url", help="url description", required=True)
        git_report_parser.add_argument("-p", "--path", help="path description", required=True)
        git_report_parser.add_argument("-b", "--branch", help="branch description")
        git_report_parser.add_argument("-t", "--env_token", help="env_token description")
        self._add_argument_output(git_report_parser)
        if include_report_options:
            self._add_group_by(git_report_parser)
            self._add_sort_by(git_report_parser)

        # Subparser for maven report
        maven_report_parser = parser.add_parser("maven", help="maven source")
        maven_report_parser.add_argument("-u", "--url", help="url description", required=False)
        maven_report_parser.add_argument("-t", "--env_token", help="env_token description")
        maven_report_parser.add_argument("--group_id", help="group_id description", required=True)
        maven_report_parser.add_argument("--artifact_id", help="artifact_id description", required=True)
        maven_report_parser.add_argument("--version", help="version description", required=True)
        maven_report_parser.add_argument("--classifier", help="classifier description")
        self._add_argument_output(maven_report_parser)
        if include_report_options:
            self._add_group_by(maven_report_parser)
            self._add_sort_by(maven_report_parser)

        # Subparser for pypi report
        pypi_report_parser = parser.add_parser("pypi", help="pypi source")
        pypi_report_parser.add_argument("-u", "--url", help="url description", required=False)
        pypi_report_parser.add_argument("-t", "--env_token", help="env_token description")
        pypi_report_parser.add_argument("--package", help="package", required=True)
        pypi_report_parser.add_argument("--version", help="version description", required=True)
        self._add_argument_output(pypi_report_parser)
        if include_report_options:
            self._add_group_by(pypi_report_parser)
            self._add_sort_by(pypi_report_parser)

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

        # command: report-asciidoc
        report_parser = subparsers.add_parser("report-asciidoc", help="Generate a report in AsciiDoc")
        report_source_subparsers = report_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(report_source_subparsers)

        # command: generate-json
        generate_json_parser = subparsers.add_parser("generate-json", help="Generate JSON")

        generate_json_parser.add_argument(
            "--no-filter",
            action="store_true",
            help="Do not filter data",
            default=False,
            required=False,
        )

        generate_json_source_subparsers = generate_json_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(generate_json_source_subparsers, include_report_options=False)

        # command: status
        status_parser = subparsers.add_parser("status", help="Status on implementations and tests of requirements")
        status_parser.add_argument(
            "--check-all-reqs-met",
            action="store_true",
            help="Fail unless all requirements are implemented",
        )
        status_source_subparsers = status_parser.add_subparsers(dest="source", required=True)
        self._add_subparsers_source(status_source_subparsers)

        args = self.__parser.parse_args()

        return args

    def _get_initial_source(self, args_source: argparse.Namespace) -> LocationInterface:
        location: LocationInterface = None

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
            location = LocalLocation(path=args_source.path)

        return location

    @Requirements("REQ_035")
    def command_report(self, report_args: argparse.Namespace):
        initial_source = self._get_initial_source(report_args)

        output = report_args.output  # where to put the generated report
        result = report.ReportCommand(
            location=initial_source,
            group_by=GroupbyOptions(report_args.group_by),
            sort_by=[SortByOptions(s) for s in report_args.sort_by],
        )

        output.write(result.result)

    @Requirements("REQ_031")
    def command_generate_json(self, generate_json_args: argparse.Namespace):
        initial_source = self._get_initial_source(generate_json_args)

        filter_data = not generate_json_args.no_filter

        result = GenerateJsonCommand(location=initial_source, filter_data=filter_data)

        output = generate_json_args.output  # where to put the generated report
        output.write(result.result)

    @Requirements("REQ_029")
    def command_status(self, status_args: argparse.Namespace) -> int:
        initial_source = self._get_initial_source(status_args)
        output = status_args.output  # where to put the generated report

        result = StatusCommand(location=initial_source)
        status, nr_of_incomplete_requirements = result.result

        output.write(str(status))

        return (
            EXIT_CODE_ALL_REQS_NOT_IMPLEMENTED
            if status_args.check_all_reqs_met and nr_of_incomplete_requirements > 0
            else 0
        )

    def print_help(self):
        self.__parser.print_help(sys.stderr)


def main():
    command = Command()
    args = command.get_arguments()

    # Set the logging level based on the argument
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.WARNING))

    exit_code: int = 0

    if args.command == "report-asciidoc":
        command.command_report(report_args=args)
    elif args.command == "generate-json":
        command.command_generate_json(generate_json_args=args)
    elif args.command == "status":
        exit_code = command.command_status(status_args=args)
    else:
        command.print_help()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
