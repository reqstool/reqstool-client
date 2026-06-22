# Copyright © LFV

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.project_session import ProjectSession
from reqstool.common.models.urn_id import UrnId
from reqstool.common.queries.details import (
    get_mvr_details,
    get_requirement_details,
    get_requirement_status,
    get_requirements_status_all,
    get_svc_details,
)
from reqstool.models.annotations import AnnotationData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    RequirementData,
)
from reqstool.models.svcs import SVCData, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.services.statistics_service import StatisticsService
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository
from reqstool.locations.local_location import LocalLocation


@pytest.fixture
def session(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    s = ProjectSession(LocalLocation(path=path))
    s.build()
    yield s
    s.close()


def test_get_requirement_details_known(session):
    result = get_requirement_details("REQ_010", session.repo)
    assert result is not None
    assert result["type"] == "requirement"
    assert result["id"] == "REQ_010"
    assert "title" in result
    assert "significance" in result
    assert "description" in result
    assert "lifecycle" in result
    assert isinstance(result["references"], list)
    assert isinstance(result["implementations"], list)
    assert isinstance(result["svcs"], list)
    assert "location" in result
    assert result["source_paths"] == {}  # no urn_source_paths passed


def test_get_requirement_details_with_source_paths(session):
    result = get_requirement_details("REQ_010", session.repo, session.urn_source_paths)
    assert result is not None
    assert isinstance(result["source_paths"], dict)


def test_get_requirement_details_unknown(session):
    assert get_requirement_details("REQ_NONEXISTENT", session.repo) is None


def test_get_requirement_details_implementations(session):
    result = get_requirement_details("REQ_010", session.repo, session.urn_source_paths)
    assert result is not None
    assert len(result["implementations"]) > 0
    impl = result["implementations"][0]
    assert "element_kind" in impl
    assert "fqn" in impl


def test_get_svc_details_known(session):
    repo = session.repo
    svc_ids = [uid.id for uid in repo.get_all_svcs()]
    assert svc_ids
    result = get_svc_details(svc_ids[0], repo)
    assert result is not None
    assert result["type"] == "svc"
    assert "title" in result
    assert "verification" in result
    assert "requirement_ids" in result
    assert "test_summary" in result
    assert set(result["test_summary"].keys()) == {"passed", "failed", "skipped", "missing"}
    assert "mvrs" in result


def test_get_svc_details_unknown(session):
    assert get_svc_details("SVC_NONEXISTENT", session.repo) is None


def test_get_svc_details_requirement_ids_enriched(session):
    repo = session.repo
    svc_ids = [uid.id for uid in repo.get_all_svcs()]
    for svc_id in svc_ids:
        result = get_svc_details(svc_id, repo)
        assert result is not None
        for req_entry in result["requirement_ids"]:
            assert "id" in req_entry
            assert "urn" in req_entry
            assert "title" in req_entry
            assert "lifecycle_state" in req_entry
        break


def test_get_mvr_details_unknown(session):
    assert get_mvr_details("MVR_NONEXISTENT", session.repo) is None


def test_get_requirement_status_known(session):
    result = get_requirement_status("REQ_010", session.repo)
    assert result is not None
    assert result["id"] == "REQ_010"
    assert "lifecycle_state" in result
    assert "implementation_type" in result
    assert "automated_tests" in result
    assert set(result["automated_tests"].keys()) == {"total", "passed", "failed", "skipped", "missing", "not_applicable"}
    assert "manual_tests" in result
    assert set(result["manual_tests"].keys()) == {"total", "passed", "failed", "skipped", "missing", "not_applicable"}
    assert "completed" in result
    assert isinstance(result["completed"], bool)


def test_get_requirement_status_unknown(session):
    assert get_requirement_status("REQ_NONEXISTENT", session.repo) is None


@pytest.mark.parametrize("include_post_build", [False, True])
@SVCs("SVC_MCP_0005")
def test_mcp_status_tools_agree_with_statistics_service(session, include_post_build):
    """get_requirement_status / get_requirements_status must report the same verdict and
    shape as StatisticsService for every requirement, in both build-only and post-build
    scoping modes — the consolidation this change exists to guarantee (issue #412)."""
    repo = session.repo
    stats = StatisticsService(repo, include_post_build=include_post_build)
    expected = stats.to_status_dict()["requirements"]

    all_results = {r["id"]: r for r in get_requirements_status_all(repo, include_post_build=include_post_build)}

    assert "REQ_ext002_300" in all_results, "fixture must cover the previously divergent requirement"

    for urn_id_str, expected_status in expected.items():
        # urn_id_str is the full "urn:id" form; pass it through unsplit so get_requirement_status
        # resolves requirements that don't live in the project's initial urn (e.g. ext-002:*).
        single_result = get_requirement_status(urn_id_str, repo, include_post_build=include_post_build)
        bare_id = urn_id_str.rsplit(":", 1)[1]

        for key in ("completed", "implementation_type", "automated_tests", "manual_tests"):
            assert single_result[key] == expected_status[key], f"{urn_id_str}: get_requirement_status[{key}] mismatch"
            assert all_results[bare_id][key] == expected_status[key], (
                f"{urn_id_str}: get_requirements_status[{key}] mismatch"
            )


def _make_db_with_req(
    impl_type,
    passed: bool | None = None,
    with_annotation: bool = False,
    verification: VERIFICATIONTYPES = VERIFICATIONTYPES.AUTOMATED_TEST,
    with_test_annotation: bool = True,
    status: TEST_RUN_STATUS | None = None,
):
    """Build a minimal in-memory DB with one requirement + SVC (+ optional test annotation/result).

    By default builds an automated-test SVC with a passing/failing automated test result (driven by
    `passed`). Pass `verification`/`status` to build a SVC with a different verification type and/or
    a specific test outcome, or `with_test_annotation=False` to build an SVC with no test
    annotation/result at all (the "entirely missing automated test" case).
    """
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_T")
    svc_id = UrnId(urn="ms-001", id="SVC_T")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=impl_type,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc = SVCData(id=svc_id, title="S", verification=verification, revision="1.0.0", requirement_ids=[req_id])
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    if with_annotation:
        db.insert_annotation_impl(
            req_id, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar")
        )
    if with_test_annotation:
        ann = AnnotationData(element_kind="METHOD", fully_qualified_name="test_method")
        db.insert_annotation_test(svc_id, ann)
        if status is None:
            status = TEST_RUN_STATUS.PASSED if passed else TEST_RUN_STATUS.FAILED
        db.insert_test_result("ms-001", "test_method", status)
    db.commit()
    return db, req_id


def test_meets_requirements_in_code_with_annotation_and_passing_tests():
    db, req_id = _make_db_with_req(IMPLEMENTATION.IN_CODE, passed=True, with_annotation=True)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["implementation_type"] == "in-code"
    assert result["completed"] is True
    db.close()


def test_meets_requirements_in_code_without_annotation_is_false():
    db, req_id = _make_db_with_req(IMPLEMENTATION.IN_CODE, passed=True, with_annotation=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is False
    db.close()


@pytest.mark.parametrize(
    "impl_type",
    [
        IMPLEMENTATION.NOT_APPLICABLE,
        IMPLEMENTATION.CONFIGURATION,
        IMPLEMENTATION.PLATFORM,
        IMPLEMENTATION.FRAMEWORK,
    ],
)
def test_meets_requirements_non_code_type_passing_tests_true(impl_type):
    db, req_id = _make_db_with_req(impl_type, passed=True, with_annotation=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["implementation_type"] == impl_type.value
    assert result["completed"] is True
    db.close()


@pytest.mark.parametrize(
    "impl_type",
    [
        IMPLEMENTATION.NOT_APPLICABLE,
        IMPLEMENTATION.CONFIGURATION,
        IMPLEMENTATION.PLATFORM,
        IMPLEMENTATION.FRAMEWORK,
    ],
)
def test_meets_requirements_non_code_type_failing_tests_false(impl_type):
    db, req_id = _make_db_with_req(impl_type, passed=False, with_annotation=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is False
    db.close()


def test_get_requirements_status_all_mixed_types():
    """get_requirements_status_all returns correct completed verdict for each impl type."""
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    URN = "ms-001"

    in_code_id = UrnId(urn=URN, id="REQ_CODE")
    cfg_id = UrnId(urn=URN, id="REQ_CFG")
    svc_code = UrnId(urn=URN, id="SVC_CODE")
    svc_cfg = UrnId(urn=URN, id="SVC_CFG")

    for req_id, impl_type in [(in_code_id, IMPLEMENTATION.IN_CODE), (cfg_id, IMPLEMENTATION.CONFIGURATION)]:
        req = RequirementData(
            id=req_id,
            title="T",
            significance=SIGNIFICANCETYPES.SHALL,
            description="D",
            implementation=impl_type,
            categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
            revision="1.0.0",
        )
        db.insert_requirement(req_id.urn, req)

    for svc_id, req_id in [(svc_code, in_code_id), (svc_cfg, cfg_id)]:
        svc = SVCData(
            id=svc_id,
            title="S",
            verification=VERIFICATIONTYPES.AUTOMATED_TEST,
            revision="1.0.0",
            requirement_ids=[req_id],
        )
        db.insert_svc(svc_id.urn, svc)
        ann = AnnotationData(element_kind="METHOD", fully_qualified_name=f"test_{svc_id.id}")
        db.insert_annotation_test(svc_id, ann)
        db.insert_test_result(URN, f"test_{svc_id.id}", TEST_RUN_STATUS.PASSED)

    db.insert_annotation_impl(in_code_id, AnnotationData(element_kind="METHOD", fully_qualified_name="com.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    results = {r["id"]: r for r in get_requirements_status_all(repo)}

    assert results["REQ_CODE"]["completed"] is True
    assert results["REQ_CFG"]["completed"] is True
    db.close()


def test_get_requirements_status_all_in_code_without_annotation_false():
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_NO_ANN")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc_id = UrnId(urn="ms-001", id="SVC_T")
    svc = SVCData(
        id=svc_id, title="S", verification=VERIFICATIONTYPES.AUTOMATED_TEST, revision="1.0.0", requirement_ids=[req_id]
    )
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="test_m")
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    db.insert_annotation_test(svc_id, ann)
    db.insert_test_result("ms-001", "test_m", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    results = {r["id"]: r for r in get_requirements_status_all(repo)}
    assert results["REQ_NO_ANN"]["completed"] is False
    db.close()


def test_get_requirements_status_all_urn_scoping():
    """get_requirements_status_all scoped to a URN excludes other URNs."""
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")

    for urn, req_id_str in [("ms-001", "REQ_A"), ("ms-002", "REQ_B")]:
        req_id = UrnId(urn=urn, id=req_id_str)
        req = RequirementData(
            id=req_id,
            title="T",
            significance=SIGNIFICANCETYPES.SHALL,
            description="D",
            implementation=IMPLEMENTATION.IN_CODE,
            categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
            revision="1.0.0",
        )
        db.insert_requirement(req_id.urn, req)
    db.commit()

    repo = RequirementsRepository(db)
    scoped = get_requirements_status_all(repo, urn="ms-001")
    ids = {r["id"] for r in scoped}
    assert "REQ_A" in ids
    assert "REQ_B" not in ids
    db.close()


# -- F1: MVR blind spot tests (TDD — write red first, then fix) --


def _make_db_with_mvr(impl_type, mvr_passed: bool):
    """DB with one requirement + manual-test SVC + MVR. No automated tests."""
    from reqstool.models.mvrs import MVRData

    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_MVR")
    svc_id = UrnId(urn="ms-001", id="SVC_MVR")
    mvr_id = UrnId(urn="ms-001", id="MVR_001")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=impl_type,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc = SVCData(
        id=svc_id, title="S", verification=VERIFICATIONTYPES.MANUAL_TEST, revision="1.0.0", requirement_ids=[req_id]
    )
    mvr = MVRData(id=mvr_id, passed=mvr_passed, comment="", svc_ids=[svc_id])
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    db.insert_mvr(mvr_id.urn, mvr)
    db.commit()
    return db, req_id


@pytest.mark.parametrize(
    "impl_type",
    [
        IMPLEMENTATION.NOT_APPLICABLE,
        IMPLEMENTATION.CONFIGURATION,
        IMPLEMENTATION.PLATFORM,
        IMPLEMENTATION.FRAMEWORK,
    ],
)
def test_meets_requirements_non_code_failing_mvr_is_false(impl_type):
    """Non-code req with a failing MVR must not be considered met."""
    db, req_id = _make_db_with_mvr(impl_type, mvr_passed=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is False, f"{impl_type}: failing MVR should make completed False"
    db.close()


@pytest.mark.parametrize(
    "impl_type",
    [
        IMPLEMENTATION.NOT_APPLICABLE,
        IMPLEMENTATION.CONFIGURATION,
        IMPLEMENTATION.PLATFORM,
        IMPLEMENTATION.FRAMEWORK,
    ],
)
def test_meets_requirements_non_code_passing_mvr_is_true(impl_type):
    """Non-code req with a passing MVR and no failing automated tests is met."""
    db, req_id = _make_db_with_mvr(impl_type, mvr_passed=True)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is True
    db.close()


def test_meets_requirements_in_code_failing_mvr_is_false():
    """IN_CODE req with annotation + passing auto-test but failing MVR must not be met."""
    from reqstool.models.mvrs import MVRData

    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_IC")
    svc_id = UrnId(urn="ms-001", id="SVC_IC")
    mvr_id = UrnId(urn="ms-001", id="MVR_IC")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc = SVCData(
        id=svc_id, title="S", verification=VERIFICATIONTYPES.MANUAL_TEST, revision="1.0.0", requirement_ids=[req_id]
    )
    mvr = MVRData(id=mvr_id, passed=False, comment="", svc_ids=[svc_id])
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    db.insert_annotation_impl(req_id, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.insert_mvr(mvr_id.urn, mvr)
    db.commit()

    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is False, "failing MVR should make IN_CODE completed False"
    db.close()


# -- F2: skipped/missing automated tests must not be silently treated as passing --


def test_meets_requirements_automated_skipped_test_is_false():
    """An automated-test SVC with a skipped test result must not count as met."""
    db, req_id = _make_db_with_req(
        IMPLEMENTATION.IN_CODE,
        with_annotation=True,
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        status=TEST_RUN_STATUS.SKIPPED,
    )
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["automated_tests"]["skipped"] == 1
    assert result["completed"] is False, "a skipped automated test should make completed False"
    db.close()


def test_meets_requirements_automated_zero_test_results_is_false():
    """An automated-test SVC with zero recorded test executions must count as missing, not passing."""
    db, req_id = _make_db_with_req(
        IMPLEMENTATION.IN_CODE,
        with_annotation=True,
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        with_test_annotation=False,
    )
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["automated_tests"]["missing"] == 1
    assert result["completed"] is False, "zero automated test executions should make completed False"
    db.close()


def test_get_requirements_status_all_automated_skipped_and_missing():
    """get_requirements_status_all must also flag skipped/missing automated tests as not met."""
    db, req_id = _make_db_with_req(
        IMPLEMENTATION.IN_CODE,
        with_annotation=True,
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        status=TEST_RUN_STATUS.SKIPPED,
    )
    repo = RequirementsRepository(db)
    results = {r["id"]: r for r in get_requirements_status_all(repo)}
    assert results[req_id.id]["completed"] is False
    db.close()


# ---------------------------------------------------------------------------
# Supersession in details queries
# ---------------------------------------------------------------------------


def _make_db_with_superseded_mvrs(mvr_pass_sequence: list[tuple[str, bool]]) -> tuple:
    """Build a minimal DB with multiple dated MVRs for the same SVC.

    mvr_pass_sequence: list of (iso_datetime_str, passed) in order.
    Returns (db, req_id, svc_id).
    """
    from datetime import datetime

    from reqstool.models.mvrs import MVRData

    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_SUPER")
    svc_id = UrnId(urn="ms-001", id="SVC_SUPER")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=IMPLEMENTATION.NOT_APPLICABLE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc = SVCData(
        id=svc_id,
        title="S",
        verification=VERIFICATIONTYPES.MANUAL_TEST,
        revision="1.0.0",
        requirement_ids=[req_id],
    )
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    for i, (dt_str, passed) in enumerate(mvr_pass_sequence):
        mvr_id = UrnId(urn="ms-001", id=f"MVR_{i:03d}")
        mvr = MVRData(
            id=mvr_id,
            passed=passed,
            svc_ids=[svc_id],
            date=datetime.fromisoformat(dt_str),
        )
        db.insert_mvr(mvr_id.urn, mvr)
    db.commit()
    return db, req_id, svc_id


def test_compute_meets_superseded_fail_latest_pass_is_true():
    """fail→pass: latest (passing) MVR makes the verdict completed."""
    db, req_id, _ = _make_db_with_superseded_mvrs([("2026-01-01T00:00:00Z", False), ("2026-01-02T00:00:00Z", True)])
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is True
    db.close()


def test_compute_meets_superseded_pass_latest_fail_is_false():
    """pass→fail: latest (failing) MVR makes the verdict not completed."""
    db, req_id, _ = _make_db_with_superseded_mvrs([("2026-01-01T00:00:00Z", True), ("2026-01-02T00:00:00Z", False)])
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["completed"] is False
    db.close()


def test_get_svc_details_superseded_flag():
    """get_svc_details marks older MVRs as superseded=True, latest as superseded=False."""
    db, _, svc_id = _make_db_with_superseded_mvrs([("2026-01-01T00:00:00Z", False), ("2026-01-02T00:00:00Z", True)])
    db.set_metadata("initial_urn", "ms-001")
    repo = RequirementsRepository(db)
    result = get_svc_details(svc_id.id, repo)
    assert result is not None
    mvrs = result["mvrs"]
    assert len(mvrs) == 2
    superseded = [m for m in mvrs if m["superseded"]]
    effective = [m for m in mvrs if not m["superseded"]]
    assert len(superseded) == 1
    assert len(effective) == 1
    assert effective[0]["passed"] is True
    assert effective[0]["date"] == "2026-01-02T00:00:00+00:00"
    db.close()


def test_get_mvr_details_includes_date():
    """get_mvr_details returns the date field as an ISO string."""
    from datetime import datetime

    from reqstool.models.mvrs import MVRData

    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_D")
    svc_id = UrnId(urn="ms-001", id="SVC_D")
    mvr_id = UrnId(urn="ms-001", id="MVR_D")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=IMPLEMENTATION.NOT_APPLICABLE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc = SVCData(
        id=svc_id, title="S", verification=VERIFICATIONTYPES.MANUAL_TEST, revision="1.0.0", requirement_ids=[req_id]
    )
    dt = datetime.fromisoformat("2026-03-15T09:00:00+01:00")
    mvr = MVRData(id=mvr_id, passed=True, svc_ids=[svc_id], date=dt)
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    db.insert_mvr(mvr_id.urn, mvr)
    db.commit()

    repo = RequirementsRepository(db)
    result = get_mvr_details(mvr_id.id, repo)
    assert result is not None
    assert result["date"] == dt.isoformat()
    db.close()
