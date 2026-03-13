# Copyright © LFV

from __future__ import annotations

import json

from colorama import Fore, Style
from reqstool_python_decorators.decorators.decorators import Requirements
from tabulate import tabulate

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.services.statistics_service import StatisticsService, TestStats, TotalStats
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository


@Requirements("REQ_027")
class StatusCommand:
    def __init__(self, location: LocationInterface, format: str = "console"):
        self.__initial_location: LocationInterface = location
        self.__format: str = format
        self.result = self.__status_result()

    def __status_result(self) -> tuple[str, int]:
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ) as (db, _):
            repo = RequirementsRepository(db)
            stats_service = StatisticsService(repo)

            if self.__format == "json":
                status = json.dumps(stats_service.to_status_dict(), indent=2)
            else:
                status = _status_table(stats_service=stats_service)

            return (
                status,
                stats_service.total_statistics.total_requirements
                - stats_service.total_statistics.completed_requirements,
            )


def _build_table(
    req_id: str,
    urn: str,
    impls: int,
    tests: TestStats,
    mvrs: TestStats,
    completed: bool,
    implementation: IMPLEMENTATION,
) -> list[str]:
    row = [urn]
    # add color to requirement if it's completed or not
    req_id_color = f"{Fore.GREEN}" if completed else f"{Fore.RED}"
    row.append(f"{req_id_color}{req_id}{Style.RESET_ALL}")

    # Perform check for implementations
    if implementation == IMPLEMENTATION.NOT_APPLICABLE:
        row.extend(["N/A"])
    else:
        color = Fore.GREEN if impls > 0 else Fore.RED
        row.extend([f"{color}{impls}{Style.RESET_ALL}"])
    _extend_row(tests, row, kind="automated")
    _extend_row(mvrs, row, kind="manual")
    return row


def _get_row_with_totals(stats_service: StatisticsService) -> list[str]:
    ts = stats_service.total_statistics
    total_automatic = ts.passed_automatic_tests + ts.failed_automatic_tests
    total_manual = ts.passed_manual_tests + ts.failed_manual_tests
    total_implementations = sum(
        stats.implementations
        for stats in stats_service.requirement_statistics.values()
        if stats.implementation_type != IMPLEMENTATION.NOT_APPLICABLE
    )
    auto_stats = TestStats(
        total=total_automatic,
        passed=ts.passed_automatic_tests,
        failed=ts.failed_automatic_tests,
        skipped=ts.skipped_tests,
        missing=ts.missing_automated_tests,
    )
    manual_stats = TestStats(
        total=total_manual,
        passed=ts.passed_manual_tests,
        failed=ts.failed_manual_tests,
        skipped=0,
        missing=ts.missing_manual_tests,
    )
    return [
        "Total",
        "",
        str(total_implementations),
        _format_test_cell(auto_stats),
        _format_test_cell(manual_stats),
    ]


# builds the status table
def _status_table(stats_service: StatisticsService) -> str:
    table_data = []
    headers = ["URN", "ID", "Implementation", "Automated Tests", "Manual Tests"]

    for req, stats in stats_service.requirement_statistics.items():
        table_data.append(
            _build_table(
                req_id=req.id,
                urn=req.urn,
                impls=stats.implementations,
                tests=stats.automated_tests,
                mvrs=stats.manual_tests,
                completed=stats.completed,
                implementation=stats.implementation_type,
            )
        )

    table_data.append(_get_row_with_totals(stats_service))

    col_align = ["center"] * len(headers) if table_data else []
    table = tabulate(tablefmt="fancy_grid", tabular_data=table_data, headers=headers, colalign=col_align)

    lines = table.split("\n")

    # Find a line without ANSI codes to measure visible width
    visible_table_width = 75
    for line in lines:
        if "╞" in line or "╘" in line:
            visible_table_width = len(line)
            break

    ts = stats_service.total_statistics
    header_req_data = ("\b" * len(str(ts.total_requirements))) + f"REQUIREMENTS: {str(ts.total_requirements)}"
    inner_width = visible_table_width - 2  # subtract ╒ and ╕
    title = (
        "╒" + "═" * inner_width + "╕" + f"\n│{header_req_data.center(inner_width)}│" + "\n╘" + "═" * inner_width + "╛"
    )

    table_with_title = f"{title}\n{table}\n"

    legend_line = (
        f"T = Total, {Fore.GREEN}P = Passed{Style.RESET_ALL}, "
        f"{Fore.RED}F = Failed{Style.RESET_ALL}, "
        f"{Fore.YELLOW}S = Skipped{Style.RESET_ALL}, "
        f"{_ORANGE}M = Missing{Style.RESET_ALL}"
    )

    statistics = _summarize_statistics(ts)

    status = table_with_title + legend_line + statistics

    return status


def _summarize_statistics(ts: TotalStats) -> str:
    nr_of_reqs_without_implementation = ts.without_implementation_total
    nr_of_completed_reqs_without_implementation = ts.without_implementation_completed
    code_reqs = ts.total_requirements - nr_of_reqs_without_implementation
    code_completed = ts.completed_requirements - nr_of_completed_reqs_without_implementation

    header_test_data = ("\b" * len(str(ts.total_tests))) + f"Total Tests: {str(ts.total_tests)}"
    header_svcs_data = ("\b" * len(str(ts.total_svcs))) + f"Total SVCs: {str(ts.total_svcs)}"
    CODE, NA, IMPLEMENTATIONS = __colorize_headers(
        total=ts.total_requirements,
        total_completed=ts.completed_requirements,
        total_reqs_no_impl=nr_of_reqs_without_implementation,
        completed_reqs_no_impl=nr_of_completed_reqs_without_implementation,
    )

    implementation_data = [
        [
            str(code_reqs) + __numbers_as_percentage(numerator=code_reqs, denominator=code_reqs),
            str(ts.with_implementation)
            + __numbers_as_percentage(numerator=ts.with_implementation, denominator=code_reqs),
            str(code_completed) + __numbers_as_percentage(numerator=code_completed, denominator=code_reqs),
            str(ts.total_requirements - (nr_of_reqs_without_implementation + code_completed))
            + __numbers_as_percentage(
                numerator=(ts.total_requirements - (nr_of_reqs_without_implementation + code_completed)),
                denominator=code_reqs,
            ),
            str(nr_of_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=nr_of_reqs_without_implementation,
                denominator=nr_of_reqs_without_implementation,
            ),
            str(nr_of_completed_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=nr_of_completed_reqs_without_implementation,
                denominator=nr_of_reqs_without_implementation,
            ),
            str(nr_of_reqs_without_implementation - nr_of_completed_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=(nr_of_reqs_without_implementation - nr_of_completed_reqs_without_implementation),
                denominator=nr_of_reqs_without_implementation,
            ),
        ]
    ]

    table_svc_data = [
        [
            str(ts.passed_tests) + __numbers_as_percentage(numerator=ts.passed_tests, denominator=ts.total_tests),
            str(ts.failed_tests) + __numbers_as_percentage(numerator=ts.failed_tests, denominator=ts.total_tests),
            str(ts.skipped_tests) + __numbers_as_percentage(numerator=ts.skipped_tests, denominator=ts.total_tests),
            str(ts.missing_automated_tests)
            + __numbers_as_percentage(numerator=ts.missing_automated_tests, denominator=ts.total_svcs),
            str(ts.missing_manual_tests)
            + __numbers_as_percentage(numerator=ts.missing_manual_tests, denominator=ts.total_svcs),
        ]
    ]

    implementation_headers = ["Total", "Implemented", "Verified", "Not Verified", "Total", "Verified", "Not Verified"]

    svc_headers = [
        "Passed tests",
        "Failed tests",
        "Skipped tests",
        "SVCs missing tests",
        "SVCs missing MVRs",
    ]

    svc_table = tabulate(
        tablefmt="fancy_grid",
        tabular_data=table_svc_data,
        headers=svc_headers,
        colalign=["center"] * len(table_svc_data[0]),
    )

    implementation_table = tabulate(
        tablefmt="fancy_grid",
        tabular_data=implementation_data,
        headers=implementation_headers,
        colalign=["center"] * len(implementation_data[0]),
    )

    total_tests_svcs_header = (
        "╒═══════════════════════════════════════════════════╤════════════════════════════════════════════╕"
        f"\n│                   {header_test_data}                   │"
        f"                {header_svcs_data}                │"
        "\n╘═══════════════════════════════════════════════════╧════════════════════════════════════════════╛"
    )

    test_header = (
        "╒═══════════════════════════════════════════════════════════╤═══════════════════════════════════════════╕"
        f"\n|                             {CODE}                          │                     {NA}                   │"
        "\n╘═══════════════════════════════════════════════════════════╧═══════════════════════════════════════════╛"
    )

    impl_header = (
        "╒═══════════════════════════════════════════════════════════════════════════════════════════════════════╕"
        f"\n|                                              {IMPLEMENTATIONS}                                          │"
        "\n╘═══════════════════════════════════════════════════════════════════════════════════════════════════════╛"
    )

    table_with_title = (
        f"\n{impl_header}\n{test_header}\n" f"{implementation_table}\n{total_tests_svcs_header}\n{svc_table}"
    )

    return table_with_title


def __numbers_as_percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    percentage = (numerator / denominator) * 100
    percentage_as_string = " ({:.2f}%)".format(percentage)
    return percentage_as_string


def __colorize_headers(
    total: int, total_completed: int, total_reqs_no_impl: int, completed_reqs_no_impl: int
) -> tuple[str, str, str]:
    total_code = total - total_reqs_no_impl
    total_code_completed = total_code == (total_completed - completed_reqs_no_impl)
    total_no_impl_completed = total_reqs_no_impl - completed_reqs_no_impl == 0

    CODE = f"{Fore.GREEN}{'Code'}{Style.RESET_ALL}" if total_code_completed else f"{Fore.RED}{'Code'}{Style.RESET_ALL}"
    NA = f"{Fore.GREEN}{'N/A'}{Style.RESET_ALL}" if total_no_impl_completed else f"{Fore.RED}{'N/A'}{Style.RESET_ALL}"
    IMPLEMENTATIONS = (
        f"{Fore.GREEN}{'IMPLEMENTATIONS'}{Style.RESET_ALL}"
        if total == total_completed
        else f"{Fore.RED}{'IMPLEMENTATIONS'}{Style.RESET_ALL}"
    )

    return CODE, NA, IMPLEMENTATIONS


_ORANGE = "\033[38;5;208m"
_DIM = Style.DIM


def _format_test_cell(stats: TestStats) -> str:
    """Format a TestStats into a single fixed-width string with colored counts."""
    if stats.not_applicable:
        return ""

    slots = [
        (stats.total, ""),
        (stats.passed, Fore.GREEN),
        (stats.failed, Fore.RED),
        (stats.skipped, Fore.YELLOW),
        (stats.missing, _ORANGE),
    ]

    parts = []
    for value, color in slots:
        if value == 0:
            parts.append(f"{_DIM} -{Style.RESET_ALL}")
        else:
            text = f"{value:>2}"
            if color:
                text = f"{color}{text}{Style.RESET_ALL}"
            parts.append(text)

    return " ".join(parts)


def _extend_row(result: TestStats, row: list[str], kind: str) -> None:
    row.append(_format_test_cell(result))
