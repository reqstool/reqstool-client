import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    NON_CODE_IMPLEMENTATIONS,
    SIGNIFICANCETYPES,
    RequirementData,
)
from reqstool.models.svcs import SVCData, VERIFICATIONPHASE, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.services.statistics_service import StatisticsService, TestStats
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository


URN = "ms-001"
REQ_ID = UrnId(urn=URN, id="REQ_001")
SVC_ID = UrnId(urn=URN, id="SVC_001")
MVR_ID = UrnId(urn=URN, id="MVR_001")


@pytest.fixture
def db():
    database = RequirementsDatabase()
    yield database
    database.close()


def _insert_req(db, req_id=REQ_ID, implementation=IMPLEMENTATION.IN_CODE):
    req = RequirementData(
        id=req_id,
        title="Req",
        significance=SIGNIFICANCETYPES.SHALL,
        description="Desc",
        implementation=implementation,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    db.insert_requirement(req_id.urn, req)


def _insert_svc(
    db,
    svc_id=SVC_ID,
    req_ids=None,
    verification=VERIFICATIONTYPES.AUTOMATED_TEST,
    phase=VERIFICATIONPHASE.BUILD,
):
    svc = SVCData(
        id=svc_id,
        title="SVC",
        verification=verification,
        phase=phase,
        revision="1.0.0",
        requirement_ids=req_ids or [REQ_ID],
    )
    db.insert_svc(svc_id.urn, svc)


def _insert_mvr(db, mvr_id=MVR_ID, svc_ids=None, passed=True):
    mvr = MVRData(id=mvr_id, passed=passed, comment="OK", svc_ids=svc_ids or [SVC_ID])
    db.insert_mvr(mvr_id.urn, mvr)


# -- TestStats --


def test_test_stats_not_applicable_is_completed():
    assert TestStats(not_applicable=True).is_completed() is True


def test_test_stats_missing_is_not_completed():
    assert TestStats(missing=1).is_completed() is False


def test_test_stats_all_passed_is_completed():
    assert TestStats(total=3, passed=3).is_completed() is True


def test_test_stats_some_failed_is_not_completed():
    assert TestStats(total=3, passed=2, failed=1).is_completed() is False


def test_test_stats_zero_total_is_not_completed():
    assert TestStats(total=0).is_completed() is False


# -- StatisticsService: completed requirement --


def test_completed_requirement_with_automated_tests(db):
    _insert_req(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.insert_test_result(URN, "com.example.FooTest.testBar", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert stats.requirement_statistics[REQ_ID].completed is True
    assert stats.total_statistics.total_requirements == 1
    assert stats.total_statistics.completed_requirements == 1
    assert stats.total_statistics.with_implementation == 1


def test_incomplete_requirement_missing_tests(db):
    _insert_req(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert stats.requirement_statistics[REQ_ID].completed is False
    assert stats.total_statistics.missing_automated_tests == 1


def test_incomplete_requirement_no_implementations(db):
    _insert_req(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_test_result(URN, "com.example.FooTest.testBar", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert stats.requirement_statistics[REQ_ID].completed is False
    assert stats.total_statistics.with_implementation == 0


# -- Non-code implementation types --


def test_not_applicable_implementation(db):
    req_id = UrnId(urn=URN, id="REQ_NA")
    _insert_req(db, req_id=req_id, implementation=IMPLEMENTATION.NOT_APPLICABLE)
    svc_id = UrnId(urn=URN, id="SVC_NA")
    _insert_svc(db, svc_id=svc_id, req_ids=[req_id], verification=VERIFICATIONTYPES.MANUAL_TEST)
    mvr_id = UrnId(urn=URN, id="MVR_NA")
    _insert_mvr(db, mvr_id=mvr_id, svc_ids=[svc_id], passed=True)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert stats.total_statistics.without_implementation_total == 1
    assert stats.total_statistics.without_implementation_completed == 1


@pytest.mark.parametrize(
    "impl_type, total_attr, completed_attr",
    [
        (IMPLEMENTATION.CONFIGURATION, "configuration_total", "configuration_completed"),
        (IMPLEMENTATION.PLATFORM, "platform_total", "platform_completed"),
        (IMPLEMENTATION.FRAMEWORK, "framework_total", "framework_completed"),
    ],
)
def test_non_code_implementation_type_completed(db, impl_type, total_attr, completed_attr):
    req_id = UrnId(urn=URN, id="REQ_NC")
    _insert_req(db, req_id=req_id, implementation=impl_type)
    svc_id = UrnId(urn=URN, id="SVC_NC")
    _insert_svc(db, svc_id=svc_id, req_ids=[req_id], verification=VERIFICATIONTYPES.MANUAL_TEST)
    mvr_id = UrnId(urn=URN, id="MVR_NC")
    _insert_mvr(db, mvr_id=mvr_id, svc_ids=[svc_id], passed=True)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert getattr(stats.total_statistics, total_attr) == 1
    assert getattr(stats.total_statistics, completed_attr) == 1
    assert stats.requirement_statistics[req_id].completed is True


_ALL_NON_CODE = sorted(NON_CODE_IMPLEMENTATIONS, key=lambda x: x.value)


@pytest.mark.parametrize(
    "impl_type, total_attr, completed_attr",
    [
        (IMPLEMENTATION.CONFIGURATION, "configuration_total", "configuration_completed"),
        (IMPLEMENTATION.PLATFORM, "platform_total", "platform_completed"),
        (IMPLEMENTATION.FRAMEWORK, "framework_total", "framework_completed"),
    ],
)
def test_non_code_implementation_type_not_completed(db, impl_type, total_attr, completed_attr):
    req_id = UrnId(urn=URN, id="REQ_NC")
    _insert_req(db, req_id=req_id, implementation=impl_type)
    svc_id = UrnId(urn=URN, id="SVC_NC")
    _insert_svc(db, svc_id=svc_id, req_ids=[req_id], verification=VERIFICATIONTYPES.MANUAL_TEST)
    mvr_id = UrnId(urn=URN, id="MVR_NC")
    _insert_mvr(db, mvr_id=mvr_id, svc_ids=[svc_id], passed=False)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert getattr(stats.total_statistics, total_attr) == 1
    assert getattr(stats.total_statistics, completed_attr) == 0
    assert stats.requirement_statistics[req_id].completed is False


@pytest.mark.parametrize("impl_type", _ALL_NON_CODE)
def test_non_code_implementation_with_annotation_raises(db, impl_type):
    req_id = UrnId(urn=URN, id="REQ_ERR")
    _insert_req(db, req_id=req_id, implementation=impl_type)
    db.insert_annotation_impl(req_id, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    with pytest.raises(TypeError, match="should not have an implementation"):
        StatisticsService(repo)


@pytest.mark.parametrize("impl_type", _ALL_NON_CODE)
def test_non_code_implementation_type_in_row(db, impl_type):
    req_id = UrnId(urn=URN, id="REQ_TYPE")
    _insert_req(db, req_id=req_id, implementation=impl_type)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)
    assert stats.requirement_statistics[req_id].implementation_type is impl_type


# -- MVR stats --


def test_manual_test_passed(db):
    _insert_req(db)
    _insert_svc(db, verification=VERIFICATIONTYPES.MANUAL_TEST)
    _insert_mvr(db, passed=True)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert stats.requirement_statistics[REQ_ID].manual_tests.passed == 1
    assert stats.total_statistics.passed_manual_tests == 1


def test_manual_test_failed(db):
    _insert_req(db)
    _insert_svc(db, verification=VERIFICATIONTYPES.MANUAL_TEST)
    _insert_mvr(db, passed=False)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    assert stats.requirement_statistics[REQ_ID].manual_tests.failed == 1
    assert stats.total_statistics.failed_manual_tests == 1


# -- Totals --


def test_total_svcs(db):
    _insert_req(db)
    _insert_svc(db, SVC_ID)
    _insert_svc(db, UrnId(urn=URN, id="SVC_002"), req_ids=[REQ_ID])
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)
    assert stats.total_statistics.total_svcs == 2


def test_empty_database(db):
    db.commit()
    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)

    ts = stats.total_statistics
    assert ts.total_requirements == 0
    assert ts.completed_requirements == 0
    assert ts.total_svcs == 0
    assert ts.total_tests == 0


# -- to_status_dict --


def test_to_status_dict_structure(db):
    db.set_metadata("initial_urn", URN)
    _insert_req(db)
    _insert_svc(db)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)
    d = stats.to_status_dict()

    assert "metadata" in d
    assert d["metadata"]["initial_urn"] == URN
    assert "requirements" in d
    assert "totals" in d
    assert "tests" in d["totals"]
    assert "automated_tests" in d["totals"]
    assert "manual_tests" in d["totals"]
    reqs_totals = d["totals"]["requirements"]
    assert "configuration" in reqs_totals
    assert "platform" in reqs_totals
    assert "framework" in reqs_totals
    assert "without_implementation" in reqs_totals
    for key in ("configuration", "platform", "framework", "without_implementation"):
        assert "total" in reqs_totals[key]
        assert "completed" in reqs_totals[key]


def test_total_stats_non_code_properties():
    from reqstool.services.statistics_service import TotalStats

    ts = TotalStats(
        without_implementation_total=1,
        without_implementation_completed=1,
        configuration_total=2,
        configuration_completed=1,
        platform_total=3,
        platform_completed=2,
        framework_total=4,
        framework_completed=0,
    )
    assert ts.non_code_total == 10
    assert ts.non_code_completed == 4


def test_total_stats_non_code_properties_all_zero():
    from reqstool.services.statistics_service import TotalStats

    ts = TotalStats()
    assert ts.non_code_total == 0
    assert ts.non_code_completed == 0


# -- phase: post-build --


def test_post_build_svc_is_non_gating_by_default(db):
    _insert_req(db)
    _insert_svc(db, phase=VERIFICATIONPHASE.POST_BUILD)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.E2ETest.testFlow")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    # No include_post_build — post-build SVC should be non-gating; req still incomplete due to no impl verdict
    stats = StatisticsService(repo, include_post_build=False)

    req_status = stats.requirement_statistics[REQ_ID]
    # automated_tests should be not_applicable (no build-phase automated-test SVCs)
    assert req_status.automated_tests.not_applicable is True
    # requirement is incomplete because there are no build-phase SVCs to verify against
    assert req_status.completed is False


def test_post_build_svc_gates_when_include_post_build_true_and_test_passes(db):
    _insert_req(db)
    _insert_svc(db, phase=VERIFICATIONPHASE.POST_BUILD)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.E2ETest.testFlow")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.insert_test_result(URN, "com.example.E2ETest.testFlow", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo, include_post_build=True)

    req_status = stats.requirement_statistics[REQ_ID]
    assert req_status.automated_tests.passed == 1
    assert req_status.completed is True


def test_post_build_svc_gates_when_include_post_build_true_and_test_missing(db):
    _insert_req(db)
    _insert_svc(db, phase=VERIFICATIONPHASE.POST_BUILD)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.E2ETest.testFlow")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo, include_post_build=True)

    req_status = stats.requirement_statistics[REQ_ID]
    assert req_status.automated_tests.missing == 1
    assert req_status.completed is False


def test_build_svc_gates_regardless_of_include_post_build(db):
    _insert_req(db)
    svc_build = UrnId(urn=URN, id="SVC_BUILD")
    _insert_svc(db, svc_id=svc_build, phase=VERIFICATIONPHASE.BUILD)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.UnitTest.testUnit")
    db.insert_annotation_test(svc_build, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.insert_test_result(URN, "com.example.UnitTest.testUnit", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo, include_post_build=False)

    req_status = stats.requirement_statistics[REQ_ID]
    assert req_status.automated_tests.passed == 1
    assert req_status.completed is True


def test_mixed_phase_only_build_svc_gates_by_default(db):
    _insert_req(db)
    svc_build = UrnId(urn=URN, id="SVC_BUILD")
    svc_post = UrnId(urn=URN, id="SVC_POST")
    _insert_svc(db, svc_id=svc_build, phase=VERIFICATIONPHASE.BUILD)
    _insert_svc(db, svc_id=svc_post, phase=VERIFICATIONPHASE.POST_BUILD)
    ann_unit = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.UnitTest.testUnit")
    ann_e2e = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.E2ETest.testFlow")
    db.insert_annotation_test(svc_build, ann_unit)
    db.insert_annotation_test(svc_post, ann_e2e)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.insert_test_result(URN, "com.example.UnitTest.testUnit", TEST_RUN_STATUS.PASSED)
    # No e2e result inserted
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo, include_post_build=False)

    req_status = stats.requirement_statistics[REQ_ID]
    # Build SVC passed; post-build SVC non-gating → requirement completed
    assert req_status.automated_tests.passed == 1
    assert req_status.completed is True


def test_statistics_service_default_excludes_post_build(db):
    _insert_req(db)
    _insert_svc(db, phase=VERIFICATIONPHASE.POST_BUILD)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.E2ETest.testFlow")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo)  # no include_post_build kwarg — default is False

    req_status = stats.requirement_statistics[REQ_ID]
    assert req_status.automated_tests.not_applicable is True


def test_post_build_manual_test_svc_is_non_gating_by_default(db):
    _insert_req(db, implementation=IMPLEMENTATION.NOT_APPLICABLE)
    _insert_svc(db, verification=VERIFICATIONTYPES.MANUAL_TEST, phase=VERIFICATIONPHASE.POST_BUILD)
    _insert_mvr(db, passed=True)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo, include_post_build=False)

    req_status = stats.requirement_statistics[REQ_ID]
    assert req_status.manual_tests.not_applicable is True


def test_post_build_manual_test_svc_gates_when_include_post_build_true(db):
    _insert_req(db, implementation=IMPLEMENTATION.NOT_APPLICABLE)
    _insert_svc(db, verification=VERIFICATIONTYPES.MANUAL_TEST, phase=VERIFICATIONPHASE.POST_BUILD)
    _insert_mvr(db, passed=True)
    db.commit()

    repo = RequirementsRepository(db)
    stats = StatisticsService(repo, include_post_build=True)

    req_status = stats.requirement_statistics[REQ_ID]
    assert req_status.manual_tests.passed == 1
    assert req_status.completed is True
