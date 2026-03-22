# Copyright © LFV

from __future__ import annotations

import json
import re
import shutil

from rich.columns import Columns
from rich.console import Console
from rich.table import Table, box
from rich.text import Text
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.services.statistics_service import StatisticsService, TestStats, TotalStats
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository


_ORANGE = "dark_orange"
_DIM = "dim"
_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _make_console() -> Console:
    width = max(80, shutil.get_terminal_size((120, 24)).columns)
    return Console(highlight=False, force_terminal=True, color_system="standard", width=width)


def _render(*renderables) -> str:
    console = _make_console()
    with console.capture() as cap:
        for r in renderables:
            console.print(r)
    return cap.get()


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


def _format_test_cell(stats: TestStats) -> Text:
    """Format a TestStats into a Rich Text object with colored counts."""
    if stats.not_applicable:
        return Text()

    def _slot(value: int, style: str) -> Text:
        t = Text()
        if value == 0:
            t.append(" -", style=_DIM)
        else:
            t.append(f"{value:>2}", style=style)
        return t

    cell = Text()
    cell.append_text(_slot(stats.total, "default"))
    cell.append(" ")
    cell.append_text(_slot(stats.passed, "green"))
    cell.append(" ")
    cell.append_text(_slot(stats.failed, "red"))
    cell.append(" ")
    cell.append_text(_slot(stats.skipped, "yellow"))
    cell.append(" ")
    cell.append_text(_slot(stats.missing, _ORANGE))
    return cell


def _build_table(
    req_id: str,
    urn: str,
    impls: int,
    tests: TestStats,
    mvrs: TestStats,
    completed: bool,
    implementation: IMPLEMENTATION,
) -> list:
    id_style = "green" if completed else "red"
    row = [
        Text(urn),
        Text(req_id, style=id_style),
    ]
    if implementation == IMPLEMENTATION.NOT_APPLICABLE:
        row.append(Text("N/A", style="dim"))
    else:
        impl_style = "green" if impls > 0 else "red"
        row.append(Text(str(impls), style=impl_style))
    row.append(_format_test_cell(tests))
    row.append(_format_test_cell(mvrs))
    return row


def _get_row_with_totals(stats_service: StatisticsService) -> list:
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
        Text("Total"),
        Text(""),
        Text(str(total_implementations)),
        _format_test_cell(auto_stats),
        _format_test_cell(manual_stats),
    ]


def _status_table(stats_service: StatisticsService) -> str:
    ts = stats_service.total_statistics

    legend = Text("T = Total, ")
    legend.append("P = Passed", style="green")
    legend.append(", ")
    legend.append("F = Failed", style="red")
    legend.append(", ")
    legend.append("S = Skipped", style="yellow")
    legend.append(", ")
    legend.append("M = Missing", style=_ORANGE)

    table = Table(
        box=box.DOUBLE_EDGE,
        show_header=True,
        header_style="bold",
        show_lines=True,
        title=f"REQUIREMENTS: {ts.total_requirements}",
        title_style="bold",
        caption=legend,
    )
    table.add_column("URN", justify="center")
    table.add_column("ID", justify="left")
    table.add_column("Implementation", justify="center")
    table.add_column("Automated Tests", justify="center")
    table.add_column("Manual Tests", justify="center")

    for req, stats in stats_service.requirement_statistics.items():
        table.add_row(
            *_build_table(
                req_id=req.id,
                urn=req.urn,
                impls=stats.implementations,
                tests=stats.automated_tests,
                mvrs=stats.manual_tests,
                completed=stats.completed,
                implementation=stats.implementation_type,
            )
        )

    table.add_section()
    table.add_row(*_get_row_with_totals(stats_service))

    statistics = _summarize_statistics(ts)

    return _render(table) + statistics


def _summarize_statistics(ts: TotalStats) -> str:
    nr_of_reqs_without_implementation = ts.without_implementation_total
    nr_of_completed_reqs_without_implementation = ts.without_implementation_completed
    code_reqs = ts.total_requirements - nr_of_reqs_without_implementation
    code_completed = ts.completed_requirements - nr_of_completed_reqs_without_implementation

    CODE, NA, IMPLEMENTATIONS = __colorize_headers()

    # Code group: 4 stats (total, implemented, verified, not verified)
    code_table = Table(box=box.DOUBLE_EDGE, show_header=True, title=CODE, title_justify="center")
    code_table.add_column("Total", justify="center")
    code_table.add_column("Implemented", justify="center")
    code_table.add_column("Verified", justify="center")
    code_table.add_column("Not Verified", justify="center")
    code_table.add_row(
        str(code_reqs) + __numbers_as_percentage(numerator=code_reqs, denominator=code_reqs),
        str(ts.with_implementation)
        + __numbers_as_percentage(numerator=ts.with_implementation, denominator=code_reqs),
        str(code_completed) + __numbers_as_percentage(numerator=code_completed, denominator=code_reqs),
        str(ts.total_requirements - (nr_of_reqs_without_implementation + code_completed))
        + __numbers_as_percentage(
            numerator=(ts.total_requirements - (nr_of_reqs_without_implementation + code_completed)),
            denominator=code_reqs,
        ),
    )

    # N/A group: 3 stats (total, verified, not verified)
    na_table = Table(box=box.DOUBLE_EDGE, show_header=True, title=NA, title_justify="center")
    na_table.add_column("Total", justify="center")
    na_table.add_column("Verified", justify="center")
    na_table.add_column("Not Verified", justify="center")
    na_table.add_row(
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
    )

    tests_table = Table(box=box.DOUBLE_EDGE, show_header=True, title=f"Total Tests: {ts.total_tests}", title_style="white")
    tests_table.add_column("Passed tests", justify="center")
    tests_table.add_column("Failed tests", justify="center")
    tests_table.add_column("Skipped tests", justify="center")
    tests_table.add_row(
        str(ts.passed_tests) + __numbers_as_percentage(numerator=ts.passed_tests, denominator=ts.total_tests),
        str(ts.failed_tests) + __numbers_as_percentage(numerator=ts.failed_tests, denominator=ts.total_tests),
        str(ts.skipped_tests) + __numbers_as_percentage(numerator=ts.skipped_tests, denominator=ts.total_tests),
    )

    svcs_table = Table(box=box.DOUBLE_EDGE, show_header=True, title=f"Total SVCs: {ts.total_svcs}", title_style="white")
    svcs_table.add_column("SVCs missing tests", justify="center")
    svcs_table.add_column("SVCs missing MVRs", justify="center")
    svcs_table.add_row(
        str(ts.missing_automated_tests)
        + __numbers_as_percentage(numerator=ts.missing_automated_tests, denominator=ts.total_svcs),
        str(ts.missing_manual_tests)
        + __numbers_as_percentage(numerator=ts.missing_manual_tests, denominator=ts.total_svcs),
    )

    cols_rendered = _render(Columns([code_table, na_table]))
    cols_width = max(
        (len(_ANSI_ESCAPE.sub("", line)) for line in cols_rendered.split("\n") if line.strip()),
        default=80,
    )
    impl_console = Console(highlight=False, force_terminal=True, color_system="standard", width=cols_width)
    with impl_console.capture() as cap:
        impl_console.print(IMPLEMENTATIONS, justify="center")
    impl_header = cap.get()

    return "\n" + impl_header + cols_rendered + _render(Columns([tests_table, svcs_table]))


def __numbers_as_percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    percentage = (numerator / denominator) * 100
    percentage_as_string = " ({:.2f}%)".format(percentage)
    return percentage_as_string


def __colorize_headers() -> tuple[Text, Text, Text]:
    return Text("In Code", style="white"), Text("Not in Code", style="white"), Text("IMPLEMENTATIONS", style="bold white")
