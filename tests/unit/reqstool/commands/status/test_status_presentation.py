# Copyright © LFV

from rich.console import Console
from rich.text import Text

from reqstool.commands.status.status import _build_table, _format_test_cell, _ORANGE, _summarize_statistics
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.services.statistics_service import TestStats, TotalStats


def _render(renderable) -> str:
    """Render a Rich renderable to a string with ANSI codes."""
    console = Console(highlight=False, force_terminal=True, color_system="standard")
    with console.capture() as cap:
        console.print(renderable, end="")
    return cap.get()


# ---------------------------------------------------------------------------
# _format_test_cell
# ---------------------------------------------------------------------------


def test_format_test_cell_not_applicable():
    result = _format_test_cell(TestStats(not_applicable=True))
    assert result.plain == ""


def test_format_test_cell_all_zeros():
    result = _format_test_cell(TestStats(total=0, passed=0, failed=0, skipped=0, missing=0))
    # All slots are dim dashes
    rendered = _render(result)
    assert "\033[2m" in rendered  # dim ANSI code
    plain = result.plain.replace(" ", "").replace("-", "")
    assert plain == ""


def test_format_test_cell_mixed_values():
    result = _format_test_cell(TestStats(total=3, passed=2, failed=1, skipped=0, missing=0))
    plain = result.plain
    assert " 3" in plain
    assert " 2" in plain
    assert " 1" in plain


def test_format_test_cell_colors():
    result = _format_test_cell(TestStats(total=1, passed=1, failed=2, skipped=3, missing=4))
    rendered = _render(result)
    assert "\033[32m" in rendered  # passed is green
    assert "\033[31m" in rendered  # failed is red
    assert "\033[33m" in rendered  # skipped is yellow
    assert " 4" in result.plain  # missing value is present


def test_format_test_cell_zero_slots_are_blank():
    result = _format_test_cell(TestStats(total=5, passed=0, failed=0, skipped=0, missing=3))
    plain = result.plain
    assert " 5" in plain
    assert " 3" in plain


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
    assert row[1].style == "green"
    assert "REQ_001" in row[1].plain


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
    assert row[1].style == "red"


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
    assert row[2].plain == "N/A"


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
    assert "2" in row[2].plain
    assert row[2].style == "green"


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
    assert "0" in row[2].plain
    assert row[2].style == "red"


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
    assert row[0].plain == "ms-001"


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


def test_summarize_statistics_all_complete_has_white_header():
    """IMPLEMENTATIONS header is always white regardless of completion."""
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
    assert "\033[37m" in result  # white ANSI code
    assert "IMPLEMENTATIONS" in result


def test_summarize_statistics_incomplete_has_white_header():
    """IMPLEMENTATIONS header is always white regardless of completion."""
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
    assert "\033[37m" in result  # white ANSI code
    assert "IMPLEMENTATIONS" in result


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
