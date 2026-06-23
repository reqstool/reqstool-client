# Copyright © LFV


from dataclasses import dataclass, field

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.models.urn_id import UrnId
from reqstool.models.requirements import IMPLEMENTATION, NON_CODE_IMPLEMENTATIONS
from reqstool.models.svcs import EXPECTS_AUTOMATED_TESTS, EXPECTS_MVRS, VERIFICATIONPHASE
from reqstool.models.test_data import TEST_RUN_STATUS, TestData
from reqstool.storage.requirements_repository import RequirementsRepository

__all__ = [
    "EXPECTS_AUTOMATED_TESTS",
    "EXPECTS_MVRS",
    "StatisticsService",
    "TestStats",
    "RequirementStatus",
    "TotalStats",
    "compute_requirement_status",
    "_requirement_to_dict",
]


@dataclass(frozen=True)
class TestStats:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    missing: int = 0
    not_applicable: bool = False

    def is_completed(self) -> bool:
        if self.not_applicable:
            return True
        if self.missing > 0:
            return False
        return self.total > 0 and self.total == self.passed


@dataclass(frozen=True)
class RequirementStatus:
    completed: bool = False
    implementations: int = 0
    implementation_type: IMPLEMENTATION = IMPLEMENTATION.IN_CODE
    automated_tests: TestStats = field(default_factory=TestStats)
    manual_tests: TestStats = field(default_factory=TestStats)


@dataclass
class TotalStats:
    total_requirements: int = 0
    completed_requirements: int = 0
    with_implementation: int = 0
    without_implementation_total: int = 0
    without_implementation_completed: int = 0
    configuration_total: int = 0
    configuration_completed: int = 0
    platform_total: int = 0
    platform_completed: int = 0
    framework_total: int = 0
    framework_completed: int = 0
    total_svcs: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    missing_automated_tests: int = 0
    missing_manual_tests: int = 0
    total_manual_tests: int = 0
    total_annotated_tests: int = 0
    passed_manual_tests: int = 0
    failed_manual_tests: int = 0
    passed_automatic_tests: int = 0
    failed_automatic_tests: int = 0

    @property
    def non_code_total(self) -> int:
        return self.without_implementation_total + self.configuration_total + self.platform_total + self.framework_total

    @property
    def non_code_completed(self) -> int:
        return (
            self.without_implementation_completed
            + self.configuration_completed
            + self.platform_completed
            + self.framework_completed
        )

    @property
    def code_reqs(self) -> int:
        return self.total_requirements - self.non_code_total

    @property
    def code_completed(self) -> int:
        return self.completed_requirements - self.non_code_completed


def compute_requirement_status(
    req, repo: RequirementsRepository, *, include_post_build: bool = False
) -> RequirementStatus:
    """Compute the single "is this requirement complete?" verdict for one requirement.

    Queries the repository through its scoped per-requirement getters so callers never
    thread pre-fetched bulk tables through this signature. This is the one place the
    completion verdict is computed; every status surface (CLI, MCP, future LSP) must call
    this rather than re-deriving it.
    """
    svcs_urn_ids = repo.get_svcs_for_req(req.id)
    svcs = [s for s in (repo.get_svc(sid) for sid in svcs_urn_ids) if s is not None]
    verdict_svcs = svcs if include_post_build else [s for s in svcs if s.phase == VERIFICATIONPHASE.BUILD]
    verdict_svc_urn_ids = [s.id for s in verdict_svcs]

    should_have_mvrs = any(svc.verification in EXPECTS_MVRS for svc in verdict_svcs)
    should_have_automated_tests = any(svc.verification in EXPECTS_AUTOMATED_TESTS for svc in verdict_svcs)

    nr_of_implementations = len(repo.get_annotations_impls_for_req(req.id))

    mvr_stats = _compute_requirement_mvr_stats(repo, verdict_svc_urn_ids, verdict_svcs, should_have_mvrs)
    automated_test_stats = _compute_requirement_automated_stats(repo, verdict_svcs, should_have_automated_tests)

    implementation_ok = _check_implementation(
        urn_id=req.id, nr_of_implementations=nr_of_implementations, implementation=req.implementation
    )

    completed = (
        implementation_ok
        and mvr_stats.is_completed()
        and automated_test_stats.is_completed()
        and (should_have_mvrs or should_have_automated_tests)
    )

    return RequirementStatus(
        completed=completed,
        implementations=nr_of_implementations,
        implementation_type=req.implementation,
        automated_tests=automated_test_stats,
        manual_tests=mvr_stats,
    )


def _compute_requirement_mvr_stats(repo: RequirementsRepository, svcs_urn_ids, svcs, should_have_mvrs) -> TestStats:
    if not should_have_mvrs:
        return TestStats(not_applicable=True)

    total = 0
    passed = 0
    failed = 0
    missing = 0
    svc_map = {s.id: s for s in svcs}
    for svc_uid in svcs_urn_ids:
        svc = svc_map.get(svc_uid)
        if svc is None or svc.verification not in EXPECTS_MVRS:
            continue
        effective = repo.get_effective_mvr_for_svc(svc_uid)
        if effective is None:
            missing += 1
        elif effective.passed:
            total += 1
            passed += 1
        else:
            total += 1
            failed += 1

    return TestStats(total=total, passed=passed, failed=failed, missing=missing)


def _compute_requirement_automated_stats(
    repo: RequirementsRepository, verdict_svcs, should_have_automated_tests
) -> TestStats:
    if not should_have_automated_tests:
        return TestStats(not_applicable=True)

    tests: list[TestData] = []
    for svc in verdict_svcs:
        annotations = repo.get_annotations_tests_for_svc(svc.id)
        if annotations:
            tests.extend(repo.get_test_results_for_svc(svc.id))
        elif svc.verification in EXPECTS_AUTOMATED_TESTS:
            tests.append(TestData(fully_qualified_name="", status=TEST_RUN_STATUS.MISSING))

    return _compute_test_stats(tests=tests, svcs=verdict_svcs)


def _compute_test_stats(tests: list[TestData], svcs) -> TestStats:
    if not tests:
        no_of_missing = sum(1 for svc in svcs if svc.verification in EXPECTS_AUTOMATED_TESTS)
        return TestStats(missing=no_of_missing)

    total = len(tests)
    passed = 0
    failed = 0
    skipped = 0
    missing = 0

    for test in tests:
        if test.fully_qualified_name == "":
            total -= 1
        match test.status:
            case TEST_RUN_STATUS.PASSED:
                passed += 1
            case TEST_RUN_STATUS.FAILED:
                failed += 1
            case TEST_RUN_STATUS.SKIPPED:
                skipped += 1
            case TEST_RUN_STATUS.MISSING:
                missing += 1

    return TestStats(total=total, passed=passed, failed=failed, skipped=skipped, missing=missing)


def _check_implementation(urn_id: UrnId, nr_of_implementations: int, implementation: IMPLEMENTATION) -> bool:
    if implementation == IMPLEMENTATION.IN_CODE:
        return nr_of_implementations > 0
    if implementation in NON_CODE_IMPLEMENTATIONS:
        if nr_of_implementations > 0:
            raise TypeError(f"Requirement {urn_id} should not have an implementation")
        return True
    raise ValueError(f"Unhandled IMPLEMENTATION value: {implementation}")


def _requirement_to_dict(status: RequirementStatus) -> dict:
    """Serialize one requirement's verdict. The single shape shared by `status`/`report`/`export` and MCP."""
    return {
        "completed": status.completed,
        "implementations": status.implementations,
        "implementation_type": status.implementation_type.value,
        "automated_tests": {
            "total": status.automated_tests.total,
            "passed": status.automated_tests.passed,
            "failed": status.automated_tests.failed,
            "skipped": status.automated_tests.skipped,
            "missing": status.automated_tests.missing,
            "not_applicable": status.automated_tests.not_applicable,
        },
        "manual_tests": {
            "total": status.manual_tests.total,
            "passed": status.manual_tests.passed,
            "failed": status.manual_tests.failed,
            "skipped": status.manual_tests.skipped,
            "missing": status.manual_tests.missing,
            "not_applicable": status.manual_tests.not_applicable,
        },
    }


@Requirements("STATUS_0001")
class StatisticsService:
    def __init__(self, repository: RequirementsRepository, include_post_build: bool = False):
        self._repo = repository
        self._include_post_build = include_post_build
        self._requirement_stats: dict[UrnId, RequirementStatus] = {}
        self._totals: TotalStats = TotalStats()
        self._calculate()

    @property
    def requirement_statistics(self) -> dict[UrnId, RequirementStatus]:
        return self._requirement_stats

    @property
    def total_statistics(self) -> TotalStats:
        return self._totals

    @property
    def initial_urn(self) -> str:
        return self._repo.get_initial_urn()

    def _calculate(self):
        requirements = self._repo.get_all_requirements()
        all_svcs = self._repo.get_all_svcs()
        annotations_tests = self._repo.get_annotations_tests()
        automated_test_results = self._repo.get_automated_test_results()

        self._calculate_global_totals(all_svcs, annotations_tests, automated_test_results)

        for urn_id, req_data in requirements.items():
            self._calculate_requirement_stats(urn_id, req_data)

    def _calculate_global_totals(self, all_svcs, annotations_tests, automated_test_results):
        self._totals.total_svcs = len(all_svcs)
        self._totals.total_annotated_tests = len(automated_test_results)

        # Single aggregation query: one effective verdict per SVC, superseded excluded
        eff_total, eff_passed, eff_failed = self._repo.get_effective_mvr_verdict_counts()
        self._totals.total_manual_tests = eff_total
        self._totals.passed_manual_tests = eff_passed
        self._totals.failed_manual_tests = eff_failed
        self._totals.passed_tests += eff_passed
        self._totals.failed_tests += eff_failed
        self._totals.total_tests = self._totals.total_annotated_tests + eff_total

        self._count_automated_test_totals(annotations_tests, automated_test_results)

    def _count_automated_test_totals(self, annotations_tests, automated_test_results):
        parsed_test_annotation_urns: list[UrnId] = []
        for svc_urn_id, annotation_list in annotations_tests.items():
            for ann in annotation_list:
                test_urn_id = UrnId(urn=svc_urn_id.urn, id=ann.fully_qualified_name)
                if test_urn_id not in parsed_test_annotation_urns:
                    parsed_test_annotation_urns.append(test_urn_id)
                    if test_urn_id in automated_test_results:
                        for test_data in automated_test_results[test_urn_id]:
                            match test_data.status:
                                case TEST_RUN_STATUS.PASSED:
                                    self._totals.passed_tests += 1
                                    self._totals.passed_automatic_tests += 1
                                case TEST_RUN_STATUS.FAILED:
                                    self._totals.failed_tests += 1
                                    self._totals.failed_automatic_tests += 1
                                case TEST_RUN_STATUS.SKIPPED:
                                    self._totals.skipped_tests += 1
                                case TEST_RUN_STATUS.MISSING:
                                    self._totals.total_tests -= 1

    def _calculate_requirement_stats(self, urn_id, req_data):
        status = compute_requirement_status(req_data, self._repo, include_post_build=self._include_post_build)
        self._requirement_stats[urn_id] = status
        self._update_requirement_totals(
            req_data, status.implementations, status.completed, status.automated_tests, status.manual_tests
        )

    def _update_requirement_totals(self, req_data, nr_of_implementations, completed, automated_test_stats, mvr_stats):
        self._totals.total_requirements += 1

        if nr_of_implementations > 0:
            self._totals.with_implementation += 1

        match req_data.implementation:
            case IMPLEMENTATION.NOT_APPLICABLE:
                self._totals.without_implementation_total += 1
                if completed:
                    self._totals.without_implementation_completed += 1
            case IMPLEMENTATION.CONFIGURATION:
                self._totals.configuration_total += 1
                if completed:
                    self._totals.configuration_completed += 1
            case IMPLEMENTATION.PLATFORM:
                self._totals.platform_total += 1
                if completed:
                    self._totals.platform_completed += 1
            case IMPLEMENTATION.FRAMEWORK:
                self._totals.framework_total += 1
                if completed:
                    self._totals.framework_completed += 1
            case IMPLEMENTATION.IN_CODE:
                pass  # tracked via with_implementation above
            case _:
                raise ValueError(f"Unhandled IMPLEMENTATION value: {req_data.implementation}")

        if completed:
            self._totals.completed_requirements += 1

        if not automated_test_stats.not_applicable:
            self._totals.missing_automated_tests += automated_test_stats.missing
        if not mvr_stats.not_applicable:
            self._totals.missing_manual_tests += mvr_stats.missing

    def to_status_dict(self) -> dict:
        initial_urn = self._repo.get_initial_urn()
        filtered = self._repo.is_filtered()

        requirements = {str(urn_id): _requirement_to_dict(status) for urn_id, status in self._requirement_stats.items()}

        ts = self._totals
        totals = {
            "requirements": {
                "total": ts.total_requirements,
                "completed": ts.completed_requirements,
                "with_implementation": ts.with_implementation,
                "without_implementation": {
                    "total": ts.without_implementation_total,
                    "completed": ts.without_implementation_completed,
                },
                "configuration": {
                    "total": ts.configuration_total,
                    "completed": ts.configuration_completed,
                },
                "platform": {
                    "total": ts.platform_total,
                    "completed": ts.platform_completed,
                },
                "framework": {
                    "total": ts.framework_total,
                    "completed": ts.framework_completed,
                },
            },
            "svcs": {
                "total": ts.total_svcs,
            },
            "tests": {
                "total": ts.total_tests,
                "passed": ts.passed_tests,
                "failed": ts.failed_tests,
                "skipped": ts.skipped_tests,
                "missing_automated": ts.missing_automated_tests,
                "missing_manual": ts.missing_manual_tests,
            },
            "automated_tests": {
                "total": ts.total_annotated_tests,
                "passed": ts.passed_automatic_tests,
                "failed": ts.failed_automatic_tests,
            },
            "manual_tests": {
                "total": ts.total_manual_tests,
                "passed": ts.passed_manual_tests,
                "failed": ts.failed_manual_tests,
            },
        }

        return {
            "metadata": {
                "initial_urn": initial_urn,
                "filtered": filtered,
            },
            "requirements": requirements,
            "totals": totals,
        }
