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
    def __init__(self, location: LocationInterface):
        self.__initial_location: LocationInterface = location
        self.result = self.__status_result()

    def __status_result(self) -> Tuple[str, int]:
        statistics: StatisticsContainer = StatisticsGenerator(
            initial_location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ).result
        status = _status_table(stats_container=statistics)

        return (
            status,
            statistics._total_statistics.nr_of_total_requirements
            - statistics._total_statistics.nr_of_completed_requirements,
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
        row.extend(
            [Fore.GREEN + "Implemented" + Style.RESET_ALL if impls > 0 else Fore.RED + "Missing" + Style.RESET_ALL]
        )
    _extend_row(tests, row)
    _extend_row(mvrs, row)
    return row


def _get_row_with_totals(stats_container: StatisticsContainer) -> List[str]:
    total_automatic = (
        stats_container._total_statistics.nr_of_passed_automatic_tests
        + stats_container._total_statistics.nr_of_failed_automatic_tests
    )
    total_manual = (
        stats_container._total_statistics.nr_of_passed_manual_tests
        + stats_container._total_statistics.nr_of_failed_manual_tests
    )
    return [
        "Total",
        "",
        "",
        # Column: Automatic
        f"T{total_automatic} "
        f"{Fore.GREEN}P{stats_container._total_statistics.nr_of_passed_automatic_tests} "
        f"{Fore.RED}F{stats_container._total_statistics.nr_of_failed_automatic_tests} "
        f"{Fore.YELLOW}S{stats_container._total_statistics.nr_of_skipped_tests} "
        f"{Fore.RED}M{stats_container._total_statistics.nr_of_missing_automated_tests}{Style.RESET_ALL}",
        # Column: Manual
        f"T{total_manual}"
        f" {Fore.GREEN}P{stats_container._total_statistics.nr_of_passed_manual_tests} "
        f"{Fore.RED}F{stats_container._total_statistics.nr_of_failed_manual_tests} "
        f"{Fore.RED}M{stats_container._total_statistics.nr_of_missing_manual_tests}{Style.RESET_ALL}",
    ]


# builds the status table
def _status_table(stats_container: StatisticsContainer) -> str:
    table_data = []
    headers = ["URN", "ID", "Implementation", "Automated Tests", "Manual Tests"]
    header_req_data = (
        "\b" * len(str(stats_container._total_statistics.nr_of_total_requirements))
    ) + f"REQUIREMENTS: {str(stats_container._total_statistics.nr_of_total_requirements)}"
    title = (
        "╒═════════════════════════════════════════════════════════════════════════╕"
        f"\n│                              {header_req_data}                             │"
        "\n╘═════════════════════════════════════════════════════════════════════════╛"
    )

    for req, stats in stats_container._requirement_statistics.items():
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
    table_with_title = f"{title}\n{table}\n"
    statistics = _summarize_statistics(
        nr_of_total_reqs=stats_container._total_statistics.nr_of_total_requirements,
        nr_of_completed_reqs=stats_container._total_statistics.nr_of_completed_requirements,
        implemented=stats_container._total_statistics.nr_of_reqs_with_implementation,
        left_to_implement=stats_container._total_statistics.nr_of_total_requirements
        - (
            stats_container._total_statistics.nr_of_reqs_with_implementation
            + stats_container._total_statistics.nr_of_total_reqs_no_implementation
        ),
        total_tests=stats_container._total_statistics.nr_of_total_tests,
        passed_tests=stats_container._total_statistics.nr_of_passed_tests,
        failed_tests=stats_container._total_statistics.nr_of_failed_tests,
        skipped_tests=stats_container._total_statistics.nr_of_skipped_tests,
        missing_automated_tests=stats_container._total_statistics.nr_of_missing_automated_tests,
        missing_manual_tests=stats_container._total_statistics.nr_of_missing_manual_tests,
        nr_of_total_svcs=stats_container._total_statistics.nr_of_total_svcs,
        nr_of_reqs_without_implementation=(stats_container._total_statistics.nr_of_total_reqs_no_implementation),
        nr_of_completed_reqs_without_implementation=(
            stats_container._total_statistics.nr_of_completed_reqs_no_implementation
        ),
    )

    legend = [
        [
            "T = Total",
            Fore.GREEN + "P = Passed" + Style.RESET_ALL,
            Fore.RED + "F = Failed" + Style.RESET_ALL,
            Fore.YELLOW + "S = Skipped" + Style.RESET_ALL,
            Fore.RED + "M = Missing" + Style.RESET_ALL,
        ],
    ]

    legend_table_data = tabulate(tablefmt="fancy_grid", tabular_data=legend)

    status = table_with_title + legend_table_data + statistics

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


def _extend_row(result: TestStatisticsItem, row: List[str]) -> None:
    colored_item = ""
    if result.not_applicable:
        colored_item = f"{'N/A'}"
    else:
        colored_item = f"{'T'}{str(result.nr_of_total_tests)}"

    if result.nr_of_passed_tests > 0:
        colored_item += f"{Fore.GREEN}{' P'}{str(result.nr_of_passed_tests)}{Style.RESET_ALL}"
    if result.nr_of_failed_tests > 0:
        colored_item += f"{Fore.RED}{' F'}{str(result.nr_of_failed_tests)}{Style.RESET_ALL}"
    if result.nr_of_skipped_tests > 0:
        colored_item += f"{Fore.YELLOW}{' S'}{str(result.nr_of_skipped_tests)}{Style.RESET_ALL}"

    if result.nr_of_missing_automated_tests > 0:
        colored_item += f"{Fore.RED}{' M'}{str(result.nr_of_missing_automated_tests)}{Style.RESET_ALL}"

    if result.nr_of_missing_manual_tests > 0:
        colored_item += f"{Fore.RED}{' M'}{str(result.nr_of_missing_manual_tests)}{Style.RESET_ALL}"

    row.append(colored_item)
