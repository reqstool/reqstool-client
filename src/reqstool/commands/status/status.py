# Copyright © LFV

from typing import List, Tuple

from colorama import Fore, Style
from reqstool_python_decorators.decorators.decorators import Requirements
from tabulate import tabulate

from reqstool.commands.status.statistics_container import StatisticsContainer, TestStatisticsItem
from reqstool.commands.status.statistics_generator import StatisticsGenerator
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.models.requirements import IMPLEMENTATION


@Requirements("REQ_027")
class StatusCommand:
    def __init__(self, location: LocationInterface, format: str = "console"):
        self.__initial_location: LocationInterface = location
        self.__format: str = format
        self.result = self.__status_result()

    def __status_result(self) -> Tuple[str, int]:
        statistics: StatisticsContainer = StatisticsGenerator(
            initial_location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ).result

        if self.__format == "json":
            status = statistics.model_dump_json(indent=2)
        else:
            status = _status_table(stats_container=statistics)

        return (
            status,
            statistics.total_statistics.nr_of_total_requirements
            - statistics.total_statistics.nr_of_completed_requirements,
        )


def _build_table(
    req_id: str, urn: str, impls: int, tests: str, mvrs: str, completed: bool, implementation: IMPLEMENTATION
) -> List[str]:
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


def _get_row_with_totals(stats_container: StatisticsContainer) -> List[str]:
    ts = stats_container.total_statistics
    total_automatic = ts.nr_of_passed_automatic_tests + ts.nr_of_failed_automatic_tests
    total_manual = ts.nr_of_passed_manual_tests + ts.nr_of_failed_manual_tests
    total_implementations = sum(
        stats.nr_of_implementations
        for stats in stats_container.requirement_statistics.values()
        if stats.implementation != IMPLEMENTATION.NOT_APPLICABLE
    )
    return [
        "Total",
        "",
        str(total_implementations),
        _format_cell(total_automatic),
        _format_cell(ts.nr_of_passed_automatic_tests, Fore.GREEN),
        _format_cell(ts.nr_of_failed_automatic_tests, Fore.RED),
        _format_cell(ts.nr_of_skipped_tests, Fore.YELLOW),
        _format_cell(ts.nr_of_missing_automated_tests, Fore.RED),
        _format_cell(total_manual),
        _format_cell(ts.nr_of_passed_manual_tests, Fore.GREEN),
        _format_cell(ts.nr_of_failed_manual_tests, Fore.RED),
        "-",
        _format_cell(ts.nr_of_missing_manual_tests, Fore.RED),
    ]


def _build_merged_headers(col_widths: List[int]) -> str:
    """Build a 3-line merged header block with group headers spanning sub-columns."""
    # col_widths: widths for all 13 columns (content width, not including borders)
    # Columns 0-2: URN, ID, Implementation (vertically centered)
    # Columns 3-7: Automated Tests (T, P, F, S, M)
    # Columns 8-12: Manual Tests (T, P, F, S, M)
    sub_headers = ["T", "P", "F", "S", "M"]

    def center(text: str, width: int) -> str:
        return text.center(width)

    # Top border
    top = "╒"
    for i, w in enumerate(col_widths):
        top += "═" * (w + 2)
        if i == 2 or i == 7:
            top += "╤"
        elif i == len(col_widths) - 1:
            top += "╕"
        else:
            top += "═" if i < 2 or (3 <= i < 7) or (8 <= i < 12) else "╤"
    # Rebuild top border properly
    top = "╒"
    # URN
    top += "═" * (col_widths[0] + 2) + "╤"
    # ID
    top += "═" * (col_widths[1] + 2) + "╤"
    # Implementation
    top += "═" * (col_widths[2] + 2) + "╤"
    # Automated Tests group (cols 3-7, merged)
    auto_width = sum(col_widths[3:8]) + 2 * 5 + 4  # 5 cols * 2 padding + 4 inner separators
    top += "═" * auto_width + "╤"
    # Manual Tests group (cols 8-13, merged)
    manual_width = sum(col_widths[8:13]) + 2 * 5 + 4
    top += "═" * manual_width + "╕"

    # Row 1: group headers
    row1 = "│"
    row1 += center("", col_widths[0] + 2) + "│"
    row1 += center("", col_widths[1] + 2) + "│"
    row1 += center("", col_widths[2] + 2) + "│"
    row1 += center("Automated Tests", auto_width) + "│"
    row1 += center("Manual Tests", manual_width) + "│"

    # Divider between row1 and row2
    div = "│"
    div += " " * (col_widths[0] + 2) + "│"
    div += " " * (col_widths[1] + 2) + "│"
    div += " " * (col_widths[2] + 2) + "├"
    for i in range(3, 8):
        div += "─" * (col_widths[i] + 2)
        div += "┬" if i < 7 else "┤"
    for i in range(8, 13):
        div += "─" * (col_widths[i] + 2)
        div += "┬" if i < 12 else "┤"

    # Row 2: sub-headers
    row2 = "│"
    row2 += center("URN", col_widths[0] + 2) + "│"
    row2 += center("ID", col_widths[1] + 2) + "│"
    row2 += center("Implementation", col_widths[2] + 2) + "│"
    for i, h in enumerate(sub_headers):
        row2 += center(h, col_widths[3 + i] + 2) + "│"
    for i, h in enumerate(sub_headers):
        row2 += center(h, col_widths[8 + i] + 2) + "│"

    return f"{top}\n{row1}\n{div}\n{row2}"


def _parse_col_widths(sep_line: str) -> List[int]:
    """Parse column content widths from a tabulate separator line like ╞═══╪═══╡."""
    col_widths = []
    current_width = 0
    for ch in sep_line[1:-1]:
        if ch == "╪":
            col_widths.append(current_width)
            current_width = 0
        else:
            current_width += 1
    col_widths.append(current_width)
    return [w - 2 for w in col_widths]


def _replace_header_with_merged(table: str) -> tuple:
    """Replace tabulate's flat header with a two-row merged header. Returns (table, lines)."""
    lines = table.split("\n")
    sep_line = next((line for line in lines if "╞" in line), None)
    if sep_line:
        col_widths = _parse_col_widths(sep_line)
        merged_header = _build_merged_headers(col_widths)
        sep_idx = next(i for i, line in enumerate(lines) if "╞" in line)
        lines = [merged_header] + lines[sep_idx:]
        table = "\n".join(lines)
    return table, lines


# builds the status table
def _status_table(stats_container: StatisticsContainer) -> str:
    table_data = []
    headers = ["URN", "ID", "Implementation", "T", "P", "F", "S", "M", "T", "P", "F", "S", "M"]

    for req, stats in stats_container.requirement_statistics.items():
        table_data.append(
            _build_table(
                req_id=req.id,
                urn=req.urn,
                impls=stats.nr_of_implementations,
                tests=stats.automated_tests_stats,
                mvrs=stats.mvrs_stats,
                completed=stats.completed,
                implementation=stats.implementation,
            )
        )

    table_data.append(_get_row_with_totals(stats_container))

    col_align = ["center"] * len(headers) if table_data else []
    table = tabulate(tablefmt="fancy_grid", tabular_data=table_data, headers=headers, colalign=col_align)

    table, lines = _replace_header_with_merged(table)

    # Find a line without ANSI codes to measure visible width
    visible_table_width = 75
    for line in lines:
        if "╞" in line or "╘" in line:
            visible_table_width = len(line)
            break

    header_req_data = (
        "\b" * len(str(stats_container.total_statistics.nr_of_total_requirements))
    ) + f"REQUIREMENTS: {str(stats_container.total_statistics.nr_of_total_requirements)}"
    inner_width = visible_table_width - 2  # subtract ╒ and ╕
    title = (
        "╒" + "═" * inner_width + "╕" + f"\n│{header_req_data.center(inner_width)}│" + "\n╘" + "═" * inner_width + "╛"
    )

    table_with_title = f"{title}\n{table}\n"

    legend_line = "T = Total, P = Passed, F = Failed, S = Skipped, M = Missing"

    statistics = _summarize_statistics(
        nr_of_total_reqs=stats_container.total_statistics.nr_of_total_requirements,
        nr_of_completed_reqs=stats_container.total_statistics.nr_of_completed_requirements,
        implemented=stats_container.total_statistics.nr_of_reqs_with_implementation,
        left_to_implement=stats_container.total_statistics.nr_of_total_requirements
        - (
            stats_container.total_statistics.nr_of_reqs_with_implementation
            + stats_container.total_statistics.nr_of_total_reqs_no_implementation
        ),
        total_tests=stats_container.total_statistics.nr_of_total_tests,
        passed_tests=stats_container.total_statistics.nr_of_passed_tests,
        failed_tests=stats_container.total_statistics.nr_of_failed_tests,
        skipped_tests=stats_container.total_statistics.nr_of_skipped_tests,
        missing_automated_tests=stats_container.total_statistics.nr_of_missing_automated_tests,
        missing_manual_tests=stats_container.total_statistics.nr_of_missing_manual_tests,
        nr_of_total_svcs=stats_container.total_statistics.nr_of_total_svcs,
        nr_of_reqs_without_implementation=(stats_container.total_statistics.nr_of_total_reqs_no_implementation),
        nr_of_completed_reqs_without_implementation=(
            stats_container.total_statistics.nr_of_completed_reqs_no_implementation
        ),
    )

    status = table_with_title + legend_line + statistics

    return status


def _summarize_statistics(
    nr_of_total_reqs: int,
    nr_of_completed_reqs: int,
    implemented: int,
    left_to_implement: int,
    total_tests: int,
    passed_tests: int,
    failed_tests: int,
    skipped_tests: int,
    missing_automated_tests: int,
    missing_manual_tests: int,
    nr_of_total_svcs: int,
    nr_of_reqs_without_implementation: int,
    nr_of_completed_reqs_without_implementation: int,
) -> str:
    header_test_data = ("\b" * len(str(total_tests))) + f"Total Tests: {str(total_tests)}"
    header_svcs_data = ("\b" * len(str(nr_of_total_svcs))) + f"Total SVCs: {str(nr_of_total_svcs)}"
    CODE, NA, IMPLEMENTATIONS = __colorize_headers(
        total=nr_of_total_reqs,
        total_completed=nr_of_completed_reqs,
        total_reqs_no_impl=nr_of_reqs_without_implementation,
        completed_reqs_no_impl=nr_of_completed_reqs_without_implementation,
    )

    implementation_data = [
        [
            str(nr_of_total_reqs - nr_of_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=nr_of_total_reqs - nr_of_reqs_without_implementation,
                denominator=(nr_of_total_reqs - nr_of_reqs_without_implementation),
            ),
            str(implemented)
            + __numbers_as_percentage(
                numerator=implemented,
                denominator=(nr_of_total_reqs - nr_of_reqs_without_implementation),
            ),
            str(nr_of_completed_reqs - nr_of_completed_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=(nr_of_completed_reqs - nr_of_completed_reqs_without_implementation),
                denominator=(nr_of_total_reqs - nr_of_reqs_without_implementation),
            ),
            str(
                nr_of_total_reqs
                - (
                    nr_of_reqs_without_implementation
                    + (nr_of_completed_reqs - nr_of_completed_reqs_without_implementation)
                )
            )
            + __numbers_as_percentage(
                numerator=(
                    nr_of_total_reqs
                    - (
                        nr_of_reqs_without_implementation
                        + (nr_of_completed_reqs - nr_of_completed_reqs_without_implementation)
                    )
                ),
                denominator=(nr_of_total_reqs - nr_of_reqs_without_implementation),
            ),
            str(nr_of_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=(nr_of_reqs_without_implementation),
                denominator=(nr_of_reqs_without_implementation),
            ),
            str(nr_of_completed_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=(nr_of_completed_reqs_without_implementation),
                denominator=(nr_of_reqs_without_implementation),
            ),
            str(nr_of_reqs_without_implementation - nr_of_completed_reqs_without_implementation)
            + __numbers_as_percentage(
                numerator=(nr_of_reqs_without_implementation - nr_of_completed_reqs_without_implementation),
                denominator=(nr_of_reqs_without_implementation),
            ),
        ]
    ]

    table_svc_data = [
        [
            str(passed_tests) + __numbers_as_percentage(numerator=passed_tests, denominator=total_tests),
            str(failed_tests) + __numbers_as_percentage(numerator=failed_tests, denominator=total_tests),
            str(skipped_tests) + __numbers_as_percentage(numerator=skipped_tests, denominator=total_tests),
            str(missing_automated_tests)
            + __numbers_as_percentage(numerator=missing_automated_tests, denominator=nr_of_total_svcs),
            str(missing_manual_tests)
            + __numbers_as_percentage(numerator=missing_manual_tests, denominator=nr_of_total_svcs),
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


def _format_cell(value: int, color: str = "") -> str:
    if value == 0:
        return "-"
    return f"{color}{value}{Style.RESET_ALL}" if color else str(value)


def _extend_row(result: TestStatisticsItem, row: List[str], kind: str) -> None:
    if result.not_applicable:
        row.extend(["-", "-", "-", "-", "-"])
        return

    row.append(_format_cell(result.nr_of_total_tests))
    row.append(_format_cell(result.nr_of_passed_tests, Fore.GREEN))
    row.append(_format_cell(result.nr_of_failed_tests, Fore.RED))
    row.append(_format_cell(result.nr_of_skipped_tests, Fore.YELLOW))

    if kind == "automated":
        row.append(_format_cell(result.nr_of_missing_automated_tests, Fore.RED))
    else:
        row.append(_format_cell(result.nr_of_missing_manual_tests, Fore.RED))
