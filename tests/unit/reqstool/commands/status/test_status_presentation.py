# Copyright © LFV

from colorama import Fore

from reqstool.commands.status.statistics_container import TestStatisticsItem
from reqstool.commands.status.status import _build_table, _extend_row, _summarize_statistics
from reqstool.models.requirements import IMPLEMENTATION


# ---------------------------------------------------------------------------
# _extend_row
# ---------------------------------------------------------------------------


def test_extend_row_not_applicable():
    """not_applicable=True appends literal 'N/A'."""
    row = []
    _extend_row(TestStatisticsItem(not_applicable=True), row)
    assert row[0] == "N/A"


def test_extend_row_total_count():
    """Total test count is prefixed with 'T'."""
    row = []
    _extend_row(TestStatisticsItem(nr_of_total_tests=5), row)
    assert "T5" in row[0]


def test_extend_row_passed_tests_green():
    """Passed tests produce a green 'P' segment."""
    row = []
    _extend_row(TestStatisticsItem(nr_of_total_tests=2, nr_of_passed_tests=2), row)
    assert Fore.GREEN in row[0]
    assert "P2" in row[0]


def test_extend_row_failed_tests_red():
    """Failed tests produce a red 'F' segment."""
    row = []
    _extend_row(TestStatisticsItem(nr_of_total_tests=1, nr_of_failed_tests=1), row)
    assert Fore.RED in row[0]
    assert "F1" in row[0]


def test_extend_row_skipped_tests_yellow():
    """Skipped tests produce a yellow 'S' segment."""
    row = []
    _extend_row(TestStatisticsItem(nr_of_total_tests=1, nr_of_skipped_tests=1), row)
    assert Fore.YELLOW in row[0]
    assert "S1" in row[0]


def test_extend_row_missing_automated_tests_red():
    """Missing automated tests produce a red 'M' segment."""
    row = []
    _extend_row(TestStatisticsItem(nr_of_missing_automated_tests=3), row)
    assert Fore.RED in row[0]
    assert "M3" in row[0]


def test_extend_row_missing_manual_tests_red():
    """Missing manual tests produce a red 'M' segment."""
    row = []
    _extend_row(TestStatisticsItem(nr_of_missing_manual_tests=2), row)
    assert Fore.RED in row[0]
    assert "M2" in row[0]


# ---------------------------------------------------------------------------
# _build_table
# ---------------------------------------------------------------------------


def test_build_table_completed_req_is_green():
    """Completed requirement ID cell is coloured green."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=1,
        tests=TestStatisticsItem(not_applicable=True),
        mvrs=TestStatisticsItem(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert Fore.GREEN in row[1]
    assert "REQ_001" in row[1]


def test_build_table_incomplete_req_is_red():
    """Incomplete requirement ID cell is coloured red."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=0,
        tests=TestStatisticsItem(not_applicable=True),
        mvrs=TestStatisticsItem(not_applicable=True),
        completed=False,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert Fore.RED in row[1]


def test_build_table_not_applicable_shows_na():
    """IMPLEMENTATION.NOT_APPLICABLE produces 'N/A' in the implementation column."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=0,
        tests=TestStatisticsItem(not_applicable=True),
        mvrs=TestStatisticsItem(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.NOT_APPLICABLE,
    )
    assert row[2] == "N/A"


def test_build_table_in_code_with_impls_shows_implemented():
    """IN_CODE with impls > 0 shows 'Implemented' in green."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=2,
        tests=TestStatisticsItem(not_applicable=True),
        mvrs=TestStatisticsItem(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert "Implemented" in row[2]
    assert Fore.GREEN in row[2]


def test_build_table_in_code_no_impls_shows_missing():
    """IN_CODE with impls == 0 shows 'Missing' in red."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=0,
        tests=TestStatisticsItem(not_applicable=True),
        mvrs=TestStatisticsItem(not_applicable=True),
        completed=False,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert "Missing" in row[2]
    assert Fore.RED in row[2]


def test_build_table_urn_is_first_column():
    """First column of the row is the URN string."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=1,
        tests=TestStatisticsItem(not_applicable=True),
        mvrs=TestStatisticsItem(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert row[0] == "ms-001"


# ---------------------------------------------------------------------------
# _summarize_statistics
# ---------------------------------------------------------------------------


def test_summarize_statistics_zero_counts_no_crash():
    """_summarize_statistics must not raise when all counts are 0."""
    result = _summarize_statistics(
        nr_of_total_reqs=0,
        nr_of_completed_reqs=0,
        implemented=0,
        left_to_implement=0,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        missing_automated_tests=0,
        missing_manual_tests=0,
        nr_of_total_svcs=0,
        nr_of_reqs_without_implementation=0,
        nr_of_completed_reqs_without_implementation=0,
    )
    assert isinstance(result, str)
    assert "IMPLEMENTATIONS" in result


def test_summarize_statistics_all_complete_has_green_header():
    """All requirements complete: IMPLEMENTATIONS header is green."""
    result = _summarize_statistics(
        nr_of_total_reqs=2,
        nr_of_completed_reqs=2,
        implemented=2,
        left_to_implement=0,
        total_tests=2,
        passed_tests=2,
        failed_tests=0,
        skipped_tests=0,
        missing_automated_tests=0,
        missing_manual_tests=0,
        nr_of_total_svcs=2,
        nr_of_reqs_without_implementation=0,
        nr_of_completed_reqs_without_implementation=0,
    )
    assert Fore.GREEN in result


def test_summarize_statistics_incomplete_has_red_header():
    """Incomplete requirements: at least one header is red."""
    result = _summarize_statistics(
        nr_of_total_reqs=3,
        nr_of_completed_reqs=1,
        implemented=1,
        left_to_implement=2,
        total_tests=3,
        passed_tests=1,
        failed_tests=2,
        skipped_tests=0,
        missing_automated_tests=2,
        missing_manual_tests=0,
        nr_of_total_svcs=3,
        nr_of_reqs_without_implementation=0,
        nr_of_completed_reqs_without_implementation=0,
    )
    assert Fore.RED in result


def test_summarize_statistics_contains_percentage_string():
    """With nonzero counts, the output contains a formatted percentage."""
    result = _summarize_statistics(
        nr_of_total_reqs=4,
        nr_of_completed_reqs=2,
        implemented=2,
        left_to_implement=2,
        total_tests=4,
        passed_tests=2,
        failed_tests=2,
        skipped_tests=0,
        missing_automated_tests=0,
        missing_manual_tests=0,
        nr_of_total_svcs=4,
        nr_of_reqs_without_implementation=0,
        nr_of_completed_reqs_without_implementation=0,
    )
    assert "%" in result
