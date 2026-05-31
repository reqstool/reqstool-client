# Copyright © LFV

from rich.console import Console

import pytest

from reqstool.commands.status.status import _NON_CODE_LABELS, _build_table, _format_test_cell
from reqstool.models.requirements import IMPLEMENTATION, NON_CODE_IMPLEMENTATIONS
from reqstool.services.statistics_service import TestStats


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


@pytest.mark.parametrize(
    "impl_type, expected_label",
    [
        (IMPLEMENTATION.NOT_APPLICABLE, "N/A"),
        (IMPLEMENTATION.CONFIGURATION, "configuration"),
        (IMPLEMENTATION.PLATFORM, "platform"),
        (IMPLEMENTATION.FRAMEWORK, "framework"),
    ],
)
def test_build_table_non_code_type_shows_dim_label(impl_type, expected_label):
    """Non-code implementation types show a dim label, not a count."""
    row = _build_table(
        req_id="REQ_001",
        urn="ms-001",
        impls=0,
        tests=TestStats(not_applicable=True),
        mvrs=TestStats(not_applicable=True),
        completed=True,
        implementation=impl_type,
    )
    assert row[2].plain == expected_label
    assert row[2].style == "dim"


def test_non_code_labels_covers_all_non_code_implementations():
    """_NON_CODE_LABELS must stay in sync with NON_CODE_IMPLEMENTATIONS."""
    assert set(_NON_CODE_LABELS.keys()) == NON_CODE_IMPLEMENTATIONS
