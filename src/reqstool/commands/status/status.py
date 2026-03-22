# Copyright © LFV

from __future__ import annotations

import json
import re

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
    return Console(highlight=False, force_terminal=True, color_system="standard", width=200)


def _render(*renderables) -> str:
    console = _make_console()
    with console.capture() as cap:
        for r in renderables:
            console.print(r)
    return cap.get()


def _visual_width(rendered: str) -> int:
    """Visual width of rendered output after stripping ANSI codes."""
    return max((len(_ANSI_ESCAPE.sub("", line)) for line in rendered.split("\n") if line.strip()), default=0)


def _single_header_box(content, outer_width: int) -> Table:
    """Single-cell bordered box sized to match outer_width.

    For box.DOUBLE_EDGE with default padding (0,1):
      outer_width = 1(border) + 1(pad) + content_width + 1(pad) + 1(border)
      => content_min_width = outer_width - 4
    """
    t = Table(box=box.DOUBLE_EDGE, show_header=False)
    t.add_column("", justify="center", min_width=max(1, outer_width - 4))
    t.add_row(content)
    return t


def _two_cell_header_box(left, right, outer_width: int, split: tuple[int, int] = (1, 1)) -> Table:
    """Two-cell bordered box sized to match outer_width with given column split ratio.

    For box.DOUBLE_EDGE with default padding (0,1) and 2 columns:
      outer_width = 1(left border) + 1(pad) + col1 + 1(pad) + 1(sep) + 1(pad) + col2 + 1(pad) + 1(right border)
      => col1 + col2 = outer_width - 7
    """
    inner = max(2, outer_width - 7)
    total_parts = split[0] + split[1]
    col1_w = max(1, inner * split[0] // total_parts)
    col2_w = max(1, inner - col1_w)
    t = Table(box=box.DOUBLE_EDGE, show_header=False)
    t.add_column("", justify="center", min_width=col1_w)
    t.add_column("", justify="center", min_width=col2_w)
    t.add_row(left, right)
    return t


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

    table = Table(box=box.DOUBLE_EDGE, show_header=True, header_style="bold", show_lines=True)
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

    rendered_table = _render(table)
    table_w = _visual_width(rendered_table)

    req_box = _single_header_box(f"REQUIREMENTS: {ts.total_requirements}", table_w)

    legend = Text("T = Total, ")
    legend.append("P = Passed", style="green")
    legend.append(", ")
    legend.append("F = Failed", style="red")
    legend.append(", ")
    legend.append("S = Skipped", style="yellow")
    legend.append(", ")
    legend.append("M = Missing", style=_ORANGE)

    statistics = _summarize_statistics(ts)

    return _render(req_box) + rendered_table + _render(legend) + statistics


def _summarize_statistics(ts: TotalStats) -> str:
    nr_of_reqs_without_implementation = ts.without_implementation_total
    nr_of_completed_reqs_without_implementation = ts.without_implementation_completed
    code_reqs = ts.total_requirements - nr_of_reqs_without_implementation
    code_completed = ts.completed_requirements - nr_of_completed_reqs_without_implementation

    CODE, NA, IMPLEMENTATIONS = __colorize_headers(
        total=ts.total_requirements,
        total_completed=ts.completed_requirements,
        total_reqs_no_impl=nr_of_reqs_without_implementation,
        completed_reqs_no_impl=nr_of_completed_reqs_without_implementation,
    )

    implementation_data = [
        str(code_reqs) + __numbers_as_percentage(numerator=code_reqs, denominator=code_reqs),
        str(ts.with_implementation) + __numbers_as_percentage(numerator=ts.with_implementation, denominator=code_reqs),
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

    svc_data = [
        str(ts.passed_tests) + __numbers_as_percentage(numerator=ts.passed_tests, denominator=ts.total_tests),
        str(ts.failed_tests) + __numbers_as_percentage(numerator=ts.failed_tests, denominator=ts.total_tests),
        str(ts.skipped_tests) + __numbers_as_percentage(numerator=ts.skipped_tests, denominator=ts.total_tests),
        str(ts.missing_automated_tests)
        + __numbers_as_percentage(numerator=ts.missing_automated_tests, denominator=ts.total_svcs),
        str(ts.missing_manual_tests)
        + __numbers_as_percentage(numerator=ts.missing_manual_tests, denominator=ts.total_svcs),
    ]

    impl_table = Table(box=box.DOUBLE_EDGE, show_header=True)
    impl_table.add_column("Total", justify="center")
    impl_table.add_column("Implemented", justify="center")
    impl_table.add_column("Verified", justify="center")
    impl_table.add_column("Not Verified", justify="center")
    impl_table.add_column("Total", justify="center")
    impl_table.add_column("Verified", justify="center")
    impl_table.add_column("Not Verified", justify="center")
    impl_table.add_row(*implementation_data)

    svc_table = Table(box=box.DOUBLE_EDGE, show_header=True)
    svc_table.add_column("Passed tests", justify="center")
    svc_table.add_column("Failed tests", justify="center")
    svc_table.add_column("Skipped tests", justify="center")
    svc_table.add_column("SVCs missing tests", justify="center")
    svc_table.add_column("SVCs missing MVRs", justify="center")
    svc_table.add_row(*svc_data)

    rendered_impl = _render(impl_table)
    impl_w = _visual_width(rendered_impl)

    rendered_svc = _render(svc_table)
    svc_w = _visual_width(rendered_svc)

    impl_box = _single_header_box(IMPLEMENTATIONS, impl_w)
    code_na_box = _two_cell_header_box(CODE, NA, impl_w, split=(4, 3))
    totals_box = _two_cell_header_box(
        f"Total Tests: {ts.total_tests}",
        f"Total SVCs: {ts.total_svcs}",
        svc_w,
    )

    return _render(impl_box) + _render(code_na_box) + rendered_impl + _render(totals_box) + rendered_svc


def __numbers_as_percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    percentage = (numerator / denominator) * 100
    percentage_as_string = " ({:.2f}%)".format(percentage)
    return percentage_as_string


def __colorize_headers(
    total: int, total_completed: int, total_reqs_no_impl: int, completed_reqs_no_impl: int
) -> tuple[Text, Text, Text]:
    total_code = total - total_reqs_no_impl
    total_code_completed = total_code == (total_completed - completed_reqs_no_impl)
    total_no_impl_completed = total_reqs_no_impl - completed_reqs_no_impl == 0

    CODE = Text("Code", style="green" if total_code_completed else "red")
    NA = Text("N/A", style="green" if total_no_impl_completed else "red")
    IMPLEMENTATIONS = Text("IMPLEMENTATIONS", style="green" if total == total_completed else "red")

    return CODE, NA, IMPLEMENTATIONS
