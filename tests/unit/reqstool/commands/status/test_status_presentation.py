# Copyright © LFV

from colorama import Fore, Style

from reqstool.commands.status.status import _build_table, _extend_row, _format_test_cell, _ORANGE, _summarize_statistics
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.services.statistics_service import TestStats, TotalStats


# ---------------------------------------------------------------------------
# _format_test_cell
# ---------------------------------------------------------------------------


def test_format_test_cell_not_applicable():
    assert _format_test_cell(TestStats(not_applicable=True)) == ""


def test_format_test_cell_all_zeros():
    result = _format_test_cell(TestStats(total=0, passed=0, failed=0, skipped=0, missing=0))
    # All slots are dim dashes
    assert Style.DIM in result
    plain = result.replace(Style.DIM, "").replace(Style.RESET_ALL, "").replace(" ", "").replace("-", "")
    assert plain == ""


def test_format_test_cell_mixed_values():
    result = _format_test_cell(TestStats(total=3, passed=2, failed=1, skipped=0, missing=0))
    # Strip ANSI to check content
    plain = result.replace(Fore.GREEN, "").replace(Fore.RED, "").replace(Fore.YELLOW, "").replace(Style.RESET_ALL, "")
    assert " 3" in plain
    assert " 2" in plain
    assert " 1" in plain


def test_format_test_cell_colors():
    result = _format_test_cell(TestStats(total=1, passed=1, failed=2, skipped=3, missing=4))
    assert Fore.GREEN in result  # passed
    assert Fore.RED in result  # failed
    assert Fore.YELLOW in result  # skipped
    assert _ORANGE in result  # missing


def test_format_test_cell_zero_slots_are_blank():
    result = _format_test_cell(TestStats(total=5, passed=0, failed=0, skipped=0, missing=3))
    plain = (
        result.replace(Fore.GREEN, "")
        .replace(Fore.RED, "")
        .replace(Fore.YELLOW, "")
        .replace(_ORANGE, "")
        .replace(Style.RESET_ALL, "")
    )
    assert " 5" in plain
    assert " 3" in plain


# ---------------------------------------------------------------------------
# _extend_row
# ---------------------------------------------------------------------------


def test_extend_row_not_applicable():
    """not_applicable=True appends single empty cell."""
    row = []
    _extend_row(TestStats(not_applicable=True), row, kind="automated")
    assert len(row) == 1
    assert row[0] == ""


def test_extend_row_appends_single_cell():
    """_extend_row appends exactly one cell."""
    row = []
    _extend_row(TestStats(total=5, passed=3, failed=2), row, kind="automated")
    assert len(row) == 1


def test_extend_row_cell_contains_values():
    """The single cell contains the test counts."""
    row = []
    _extend_row(TestStats(total=5, passed=3, failed=2), row, kind="automated")
    plain = row[0].replace(Fore.GREEN, "").replace(Fore.RED, "").replace(Fore.YELLOW, "").replace(Style.RESET_ALL, "")
    assert " 5" in plain
    assert " 3" in plain
    assert " 2" in plain


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


def test_build_table_returns_5_columns():
    """Row has 5 elements: URN + ID + Impl + Automated Tests + Manual Tests."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=1,
        tests=TestStats(total=3, passed=2, failed=1),
        mvrs=TestStats(total=1, passed=1),
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
    )
    assert len(row) == 5


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
