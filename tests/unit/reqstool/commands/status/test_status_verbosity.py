# Copyright © LFV

import sqlite3

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.status.status import StatusCommand, _incomplete_reasons
from reqstool.locations.local_location import LocalLocation
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.services.statistics_service import RequirementStatus, TestStats


# ---------------------------------------------------------------------------
# _incomplete_reasons
# ---------------------------------------------------------------------------


def _make_status(
    implementation_type=IMPLEMENTATION.IN_CODE,
    implementations=2,
    auto_failed=0,
    auto_missing=0,
    manual_failed=0,
    manual_missing=0,
    auto_na=False,
    manual_na=False,
) -> RequirementStatus:
    auto = TestStats(
        total=3,
        passed=3 - auto_failed - auto_missing,
        failed=auto_failed,
        missing=auto_missing,
        not_applicable=auto_na,
    )
    manual = TestStats(
        total=2,
        passed=2 - manual_failed - manual_missing,
        failed=manual_failed,
        missing=manual_missing,
        not_applicable=manual_na,
    )
    return RequirementStatus(
        completed=False,
        implementations=implementations,
        implementation_type=implementation_type,
        automated_tests=auto,
        manual_tests=manual,
    )


def test_incomplete_reasons_not_implemented():
    s = _make_status(implementations=0)
    assert "not implemented" in _incomplete_reasons(s)


def test_incomplete_reasons_auto_failed():
    s = _make_status(auto_failed=1)
    r = _incomplete_reasons(s)
    assert "automated test failed" in r
    assert "passed)" in r  # shows X/Y passed


def test_incomplete_reasons_auto_missing():
    s = _make_status(auto_missing=1)
    assert "automated test missing" in _incomplete_reasons(s)


def test_incomplete_reasons_manual_failed():
    s = _make_status(manual_failed=1)
    assert "manual verification failed" in _incomplete_reasons(s)


def test_incomplete_reasons_manual_missing():
    s = _make_status(manual_missing=1)
    assert "manual result missing" in _incomplete_reasons(s)


def test_incomplete_reasons_multiple_combined_with_dot():
    s = _make_status(implementations=0, auto_missing=1)
    r = _incomplete_reasons(s)
    assert "not implemented" in r
    assert "automated test missing" in r
    assert " · " in r


def test_incomplete_reasons_not_applicable_stats_ignored():
    s = _make_status(auto_na=True, manual_na=True, implementations=0)
    r = _incomplete_reasons(s)
    assert "automated" not in r
    assert "manual" not in r
    assert "not implemented" in r


# ---------------------------------------------------------------------------
# CompactStatus
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_status_compact_format(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="compact",
    )
    status, _ = result.result
    assert "ms-001" in status
    assert "requirements" in status
    assert "FAIL" in status
    assert "\n" in status
    assert len(status.strip().splitlines()) == 1


@SVCs("SVC_021")
def test_status_compact_single_line(local_testdata_resources_rootdir_w_path):
    """Compact output is exactly one non-empty line regardless of fixture state."""
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        verbosity="compact",
    )
    status, _ = result.result
    non_empty = [l for l in status.splitlines() if l.strip()]
    assert len(non_empty) == 1
    assert "requirements" in non_empty[0]


# ---------------------------------------------------------------------------
# NormalStatus
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_status_normal_has_complete_and_incomplete(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="normal",
    )
    status, _ = result.result
    assert "COMPLETE" in status
    assert "INCOMPLETE" in status
    assert "FAIL" in status


@SVCs("SVC_021")
def test_status_normal_complete_before_incomplete(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="normal",
    )
    status, _ = result.result
    complete_pos = status.find("COMPLETE")
    incomplete_pos = status.find("INCOMPLETE")
    assert complete_pos < incomplete_pos, "COMPLETE section must appear before INCOMPLETE"


@SVCs("SVC_021")
def test_status_normal_verdict_at_bottom(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="normal",
    )
    status, _ = result.result
    lines = [l for l in status.rstrip().splitlines() if l.strip()]
    assert "FAIL" in lines[-1]


@SVCs("SVC_021")
def test_status_normal_has_reason_text(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="normal",
    )
    status, _ = result.result
    assert "automated test failed" in status or "automated test missing" in status or "manual" in status


# ---------------------------------------------------------------------------
# --incomplete flag
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_status_incomplete_flag_hides_complete_section(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="normal",
        incomplete=True,
    )
    status, _ = result.result
    assert "INCOMPLETE" in status
    # "COMPLETE (" is a substring of "INCOMPLETE ("; check the standalone COMPLETE section is absent
    import re
    assert not re.search(r'(?<![A-Z])COMPLETE \(', status)


@SVCs("SVC_021")
def test_status_incomplete_flag_verbose(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="verbose",
        incomplete=True,
    )
    status, _ = result.result
    assert "REQUIREMENTS" in status


# ---------------------------------------------------------------------------
# VerboseStatus (table, no %-blocks)
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_status_verbose_has_table(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="verbose",
    )
    status, _ = result.result
    assert "REQUIREMENTS" in status
    assert "URN" in status
    assert "Automated Tests" in status
    # No %-breakdown blocks
    assert "IMPLEMENTATIONS" not in status


# ---------------------------------------------------------------------------
# ExtraVerboseStatus (drill-down)
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_status_extra_verbose_has_drill_down(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="extra-verbose",
    )
    status, _ = result.result
    assert "COMPLETE" in status
    assert "INCOMPLETE" in status
    assert "implementation" in status
    assert "SVC_" in status


@SVCs("SVC_021")
def test_status_extra_verbose_shows_mvr_result(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="extra-verbose",
    )
    status, _ = result.result
    assert "MVR_" in status


@SVCs("SVC_021")
def test_status_extra_verbose_verdict_at_bottom(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        verbosity="extra-verbose",
    )
    status, _ = result.result
    lines = [l for l in status.rstrip().splitlines() if l.strip()]
    assert "FAIL" in lines[-1]


# ---------------------------------------------------------------------------
# JSON + filtering
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_status_json_default_has_all_requirements(local_testdata_resources_rootdir_w_path):
    import json

    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        format="json",
    )
    status, _ = result.result
    data = json.loads(status)
    assert len(data["requirements"]) == 6


@SVCs("SVC_021")
def test_status_json_req_ids_filter(local_testdata_resources_rootdir_w_path):
    import json

    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        format="json",
        req_ids=["REQ_010"],
    )
    status, _ = result.result
    data = json.loads(status)
    assert len(data["requirements"]) == 1
    assert "ms-001:REQ_010" in data["requirements"]


# ---------------------------------------------------------------------------
# Export sqlite
# ---------------------------------------------------------------------------


@SVCs("SVC_021")
def test_export_sqlite_produces_valid_db(local_testdata_resources_rootdir_w_path, tmp_path):
    from reqstool.common.validator_error_holder import ValidationErrorHolder
    from reqstool.common.validators.semantic_validator import SemanticValidator
    from reqstool.storage.pipeline import build_database

    dest = str(tmp_path / "export.db")
    loc = LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    with build_database(
        location=loc,
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    ) as (db, _):
        db.backup_to(dest)

    conn = sqlite3.connect(dest)
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "requirements" in tables
    assert conn.execute("SELECT count(*) FROM requirements").fetchone()[0] > 0
