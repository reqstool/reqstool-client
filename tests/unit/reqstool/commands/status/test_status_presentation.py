# Copyright © LFV

from colorama import Fore

from reqstool.commands.status.status import _build_table, _extend_row, _format_cell, _summarize_statistics
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.services.statistics_service import TestStats, TotalStats


# ---------------------------------------------------------------------------
# _format_cell
# ---------------------------------------------------------------------------


def test_format_cell_zero_returns_dash():
    assert _format_cell(0) == "-"


def test_format_cell_nonzero_without_color():
    assert _format_cell(5) == "5"


def test_format_cell_nonzero_with_color():
    result = _format_cell(3, Fore.GREEN)
    assert Fore.GREEN in result
    assert "3" in result


# ---------------------------------------------------------------------------
# _extend_row
# ---------------------------------------------------------------------------


def test_extend_row_not_applicable():
    """not_applicable=True appends five dashes."""
    row = []
    _extend_row(TestStats(not_applicable=True), row, kind="automated")
    assert len(row) == 5
    assert all(cell == "-" for cell in row)


def test_extend_row_total_count():
    """Total test count appears in first cell."""
    row = []
    _extend_row(TestStats(total=5), row, kind="automated")
    assert row[0] == "5"


def test_extend_row_passed_tests_green():
    """Passed tests produce a green cell."""
    row = []
    _extend_row(TestStats(total=2, passed=2), row, kind="automated")
    assert Fore.GREEN in row[1]
    assert "2" in row[1]


def test_extend_row_failed_tests_red():
    """Failed tests produce a red cell."""
    row = []
    _extend_row(TestStats(total=1, failed=1), row, kind="automated")
    assert Fore.RED in row[2]
    assert "1" in row[2]


def test_extend_row_skipped_tests_yellow():
    """Skipped tests produce a yellow cell."""
    row = []
    _extend_row(TestStats(total=1, skipped=1), row, kind="automated")
    assert Fore.YELLOW in row[3]
    assert "1" in row[3]


def test_extend_row_missing_automated_tests_red():
    """Missing automated tests produce a red cell."""
    row = []
    _extend_row(TestStats(missing=3), row, kind="automated")
    assert Fore.RED in row[4]
    assert "3" in row[4]


def test_extend_row_missing_manual_tests_red():
    """Missing manual tests produce a red cell."""
    row = []
    _extend_row(TestStats(missing=2), row, kind="manual")
    assert Fore.RED in row[4]
    assert "2" in row[4]


def test_extend_row_zero_values_show_dash():
    """Zero values display as dash."""
    row = []
    _extend_row(
        TestStats(total=0, passed=0, failed=0, skipped=0),
        row,
        kind="automated",
    )
    assert all(cell == "-" for cell in row)


# ---------------------------------------------------------------------------
# _build_table
# ---------------------------------------------------------------------------


def test_build_table_completed_req_is_green():
    """Completed requirement ID cell is coloured green."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=1,
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
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
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
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
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.NOT_APPLICABLE,
    )
    assert row[2] == "N/A"


def test_build_table_in_code_with_impls_shows_count():
    """IN_CODE with impls > 0 shows numeric count in green."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=2,
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert "2" in row[2]
    assert Fore.GREEN in row[2]


def test_build_table_in_code_no_impls_shows_zero():
    """IN_CODE with impls == 0 shows 0 in red."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=0,
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
        completed=False,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert "0" in row[2]
    assert Fore.RED in row[2]


def test_build_table_urn_is_first_column():
    """First column of the row is the URN string."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=1,
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert row[0] == "ms-001"


def test_build_table_returns_13_columns():
    """Row has 13 elements: URN + ID + Impl + 5 automated + 5 manual."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=1,
        tests=TestStats(total=3, passed=2, failed=1),
        mvrs=TestStats(total=1, passed=1),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert len(row) == 13


# ---------------------------------------------------------------------------
# _summarize_statistics
# ---------------------------------------------------------------------------


def test_summarize_statistics_zero_counts_no_crash():
    """_summarize_statistics must not raise when all counts are 0."""
    result = _summarize_statistics(TotalStats())
    assert isinstance(result, str)
    assert "IMPLEMENTATIONS" in result


def test_summarize_statistics_all_complete_has_green_header():
    """All requirements complete: IMPLEMENTATIONS header is green."""
    result = _summarize_statistics(
        TotalStats(
            total_requirements=2,
            completed_requirements=2,
            with_implementation=2,
            total_tests=2,
            passed_tests=2,
            total_svcs=2,
        )
    )
    assert Fore.GREEN in result


def test_summarize_statistics_incomplete_has_red_header():
    """Incomplete requirements: at least one header is red."""
    result = _summarize_statistics(
        TotalStats(
            total_requirements=3,
            completed_requirements=1,
            with_implementation=1,
            total_tests=3,
            passed_tests=1,
            failed_tests=2,
            missing_automated_tests=2,
            total_svcs=3,
        )
    )
    assert Fore.RED in result


def test_summarize_statistics_contains_percentage_string():
    """With nonzero counts, the output contains a formatted percentage."""
    result = _summarize_statistics(
        TotalStats(
            total_requirements=4,
            completed_requirements=2,
            with_implementation=2,
            total_tests=4,
            passed_tests=2,
            failed_tests=2,
            total_svcs=4,
        )
    )
    assert "%" in result
