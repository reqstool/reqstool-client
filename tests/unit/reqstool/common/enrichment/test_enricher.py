# Copyright © LFV

from unittest.mock import MagicMock, patch

from reqstool.common.enrichment.enricher import (
    BUILT_IN_PRESETS,
    _block_field,
    _format_value,
    _in_backtick_span,
    _is_stub,
    _make_pattern,
    enrich_text,
)
from reqstool.common.models.urn_id import UrnId


# ---------------------------------------------------------------------------
# _block_field
# ---------------------------------------------------------------------------


def test_block_field_single_line():
    assert _block_field("Description", "Simple one-liner") == ["**Description**: Simple one-liner"]


def test_block_field_empty():
    assert _block_field("Description", "") == []


def test_block_field_multiline():
    value = "GIVEN a component\nWHEN it is invoked\nTHEN it returns a result"
    nbsp = " " * 4
    assert _block_field("Description", value) == [
        "**Description**:",
        f"{nbsp}GIVEN a component",
        f"{nbsp}WHEN it is invoked",
        f"{nbsp}THEN it returns a result",
    ]


def test_block_field_multiline_blank_lines_preserved():
    nbsp = " " * 4
    assert _block_field("Description", "Line one\n\nLine three") == [
        "**Description**:",
        f"{nbsp}Line one",
        "",
        f"{nbsp}Line three",
    ]


# ---------------------------------------------------------------------------
# _format_value
# ---------------------------------------------------------------------------


def test_format_value_significance_shall():
    assert _format_value("shall") == "SHALL"


def test_format_value_significance_should():
    assert _format_value("should") == "SHOULD"


def test_format_value_significance_may():
    assert _format_value("may") == "MAY"


def test_format_value_na():
    assert _format_value("N/A") == "N/A"


def test_format_value_hyphenated():
    assert _format_value("automated-test") == "Automated Test"
    assert _format_value("manual-test") == "Manual Test"
    assert _format_value("in-code") == "In Code"
    assert _format_value("functional-suitability") == "Functional Suitability"


def test_format_value_single_word():
    assert _format_value("effective") == "Effective"
    assert _format_value("security") == "Security"
    assert _format_value("maintainability") == "Maintainability"


# ---------------------------------------------------------------------------
# _in_backtick_span
# ---------------------------------------------------------------------------


def test_in_backtick_span_inside():
    line = "Use `REQ_101` here"
    pos = line.index("REQ_101")
    assert _in_backtick_span(line, pos) is True


def test_in_backtick_span_outside():
    line = "Use `something` and REQ_101"
    pos = line.index("REQ_101")
    assert _in_backtick_span(line, pos) is False


def test_in_backtick_span_no_backticks():
    line = "Just REQ_101 here"
    pos = line.index("REQ_101")
    assert _in_backtick_span(line, pos) is False


# ---------------------------------------------------------------------------
# _is_stub
# ---------------------------------------------------------------------------


def test_is_stub_implement():
    assert _is_stub("The system SHALL implement REQ_101.", "REQ_101") is True


def test_is_stub_pass():
    assert _is_stub("The system SHALL pass SVC_101.", "SVC_101") is True


def test_is_stub_wrong_id():
    assert _is_stub("The system SHALL implement REQ_101.", "REQ_102") is False


def test_is_stub_not_a_stub():
    assert _is_stub("### Requirement: REQ_101", "REQ_101") is False


def test_is_stub_without_period():
    assert _is_stub("The system SHALL implement REQ_101", "REQ_101") is True


# ---------------------------------------------------------------------------
# _make_pattern
# ---------------------------------------------------------------------------


def test_make_pattern_empty():
    pattern = _make_pattern({})
    assert pattern.search("REQ_101") is None


def test_make_pattern_matches():
    from reqstool.common.enrichment.enricher import _EntityInfo

    lookup = {"REQ_101": _EntityInfo("Title", []), "SVC_101": _EntityInfo("SVC Title", [])}
    pattern = _make_pattern(lookup)
    assert pattern.search("REQ_101") is not None
    assert pattern.search("SVC_101") is not None
    assert pattern.search("UNKNOWN") is None


def test_make_pattern_word_boundary():
    from reqstool.common.enrichment.enricher import _EntityInfo

    lookup = {"REQ_101": _EntityInfo("Title", [])}
    pattern = _make_pattern(lookup)
    assert pattern.search("REQ_1010") is None
    assert pattern.search("PREFIX_REQ_101") is None


# ---------------------------------------------------------------------------
# enrich_text — pure (no DB, minimal mock data)
# ---------------------------------------------------------------------------


def test_enrich_text_empty_text():
    result = enrich_text("", {}, {}, {}, BUILT_IN_PRESETS["openspec:spec"])
    assert result == ""


def test_enrich_text_no_ids_passthrough():
    text = "Just plain text.\nNo IDs here.\n"
    result = enrich_text(text, {}, {}, {}, BUILT_IN_PRESETS["openspec:spec"])
    assert result == text


def test_enrich_text_fenced_block_skipped():
    text = "```\nREQ_101\n```\n"
    result = enrich_text(text, {}, {}, {}, BUILT_IN_PRESETS["openspec:design"])
    assert "—" not in result
    assert result == text


def _svc_201():
    svc = MagicMock()
    svc.title = "Scenario title"
    return {UrnId(urn="ms-101", id="SVC_201"): svc}


def _enrich_spec(text: str) -> str:
    with patch("reqstool.common.enrichment.enricher._svc_block_lines", return_value=[]):
        return enrich_text(text, {}, _svc_201(), {}, BUILT_IN_PRESETS["openspec:spec"])


def test_enrich_text_drops_when_then_step_stub():
    text = "#### Scenario: SVC_201\n- **WHEN** SVC_201 is run\n- **THEN** it passes\n\nNext.\n"
    assert _enrich_spec(text) == "#### Scenario: SVC_201 — Scenario title\n\nNext.\n"


def test_enrich_text_keeps_when_step_without_then_stub():
    text = "#### Scenario: SVC_201\n- **WHEN** SVC_201 is run\n- **THEN** the report lists it\n"
    assert _enrich_spec(text) == (
        "#### Scenario: SVC_201 — Scenario title\n- **WHEN** SVC_201 is run\n- **THEN** the report lists it\n"
    )


def test_enrich_text_keeps_when_step_at_end_of_text():
    text = "#### Scenario: SVC_201\n- **WHEN** SVC_201 is run"
    assert _enrich_spec(text) == "#### Scenario: SVC_201 — Scenario title\n- **WHEN** SVC_201 is run"


def test_enrich_text_keeps_when_step_for_another_id():
    text = "#### Scenario: SVC_201\n- **WHEN** SVC_202 is run\n- **THEN** it passes\n"
    assert _enrich_spec(text) == (
        "#### Scenario: SVC_201 — Scenario title\n- **WHEN** SVC_202 is run\n- **THEN** it passes\n"
    )
