# Copyright © LFV

from dataclasses import dataclass, field
from typing import Dict, List

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.models.urn_id import UrnId
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.models.svcs import VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS, TestData
from reqstool.storage.requirements_repository import RequirementsRepository

EXPECTS_MVRS = [
    VERIFICATIONTYPES.MANUAL_TEST,
    VERIFICATIONTYPES.REVIEW,
    VERIFICATIONTYPES.PLATFORM,
    VERIFICATIONTYPES.OTHER,
]
EXPECTS_AUTOMATED_TESTS = [VERIFICATIONTYPES.AUTOMATED_TEST]


@dataclass(frozen=True)
class TestStats:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    missing: int = 0
    not_applicable: bool = False

    def is_completed(self) -> bool:
        if self.missing > 0:
            return False
        return self.total == self.passed


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


@Requirements("REQ_028")
class StatisticsService:
    def __init__(self, repository: RequirementsRepository):
        self._repo = repository
        self._requirement_stats: Dict[UrnId, RequirementStatus] = {}
        self._totals: TotalStats = TotalStats()
        self._calculate()

    @property
    def requirement_statistics(self) -> Dict[UrnId, RequirementStatus]:
        return self._requirement_stats

    @property
    def total_statistics(self) -> TotalStats:
        return self._totals

    def _calculate(self):
        requirements = self._repo.get_all_requirements()
        all_svcs = self._repo.get_all_svcs()
        all_mvrs = self._repo.get_all_mvrs()
        annotations_impls = self._repo.get_annotations_impls()
        annotations_tests = self._repo.get_annotations_tests()
        automated_test_results = self._repo.get_automated_test_results()

        # Calculate totals for SVCs, manual tests, annotated tests
        self._totals.total_svcs = len(all_svcs)
        self._totals.total_manual_tests = len(all_mvrs)
        self._totals.total_annotated_tests = len(automated_test_results)
        self._totals.total_tests = self._totals.total_annotated_tests + self._totals.total_manual_tests

        # Count MVR pass/fail for totals
        for mvr_data in all_mvrs.values():
            if mvr_data.passed:
                self._totals.passed_tests += 1
                self._totals.passed_manual_tests += 1
            else:
                self._totals.failed_tests += 1
                self._totals.failed_manual_tests += 1

        # Count automated test results for totals
        parsed_test_annotation_urns: List[UrnId] = []
        for svc_urn_id, annotation_list in annotations_tests.items():
            for ann in annotation_list:
                test_urn_id = UrnId(urn=svc_urn_id.urn, id=ann.fully_qualified_name)
                if test_urn_id not in parsed_test_annotation_urns:
                    parsed_test_annotation_urns.append(test_urn_id)
                    if test_urn_id in automated_test_results:
                        for test_data in automated_test_results[test_urn_id]:
                            if test_data not in []:  # placeholder for dedup (matches original logic)
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
                                        self._totals.missing_automated_tests += 1
                                        self._totals.total_tests -= 1

        # Per-requirement statistics
        for urn_id, req_data in requirements.items():
            svcs_urn_ids = self._repo.get_svcs_for_req(urn_id)
            svcs = [all_svcs[sid] for sid in svcs_urn_ids if sid in all_svcs]

            should_have_mvrs = any(svc.verification in EXPECTS_MVRS for svc in svcs)
            should_have_automated_tests = any(svc.verification in EXPECTS_AUTOMATED_TESTS for svc in svcs)

            nr_of_implementations = len(annotations_impls.get(urn_id, []))

            # MVR stats
            mvr_ids = [mid for svc_uid in svcs_urn_ids for mid in self._repo.get_mvrs_for_svc(svc_uid)]
            mvrs = [all_mvrs[mid] for mid in mvr_ids if mid in all_mvrs]

            if should_have_mvrs:
                mvr_stats = self._get_mvr_stats(mvrs=mvrs if mvrs else None, svcs=svcs)
            else:
                mvr_stats = TestStats(not_applicable=True)

            # Automated test stats
            test_results_for_req = self._get_annotated_automated_test_results_for_req(
                svcs_urn_ids=svcs_urn_ids,
                all_svcs=all_svcs,
                annotations_tests=annotations_tests,
                automated_test_results=automated_test_results,
            )

            if should_have_automated_tests:
                automated_test_stats = self._get_test_stats(tests=test_results_for_req, svcs=svcs)
            else:
                automated_test_stats = TestStats(not_applicable=True)

            # Check implementation
            implementation_ok = self._check_implementation(
                urn_id=urn_id,
                nr_of_implementations=nr_of_implementations,
                implementation=req_data.implementation,
            )

            completed = (
                implementation_ok
                and mvr_stats.is_completed()
                and automated_test_stats.is_completed()
                and (should_have_mvrs or should_have_automated_tests)
            )

            req_status = RequirementStatus(
                completed=completed,
                implementations=nr_of_implementations,
                implementation_type=req_data.implementation,
                automated_tests=automated_test_stats,
                manual_tests=mvr_stats,
            )

            self._requirement_stats[urn_id] = req_status

            # Update totals
            self._totals.total_requirements += 1
            self._totals.missing_automated_tests += automated_test_stats.missing
            self._totals.missing_manual_tests += mvr_stats.missing

            if nr_of_implementations > 0:
                self._totals.with_implementation += 1

            if req_data.implementation == IMPLEMENTATION.NOT_APPLICABLE:
                self._totals.without_implementation_total += 1
                if completed:
                    self._totals.without_implementation_completed += 1

            if completed:
                self._totals.completed_requirements += 1

    def _check_implementation(self, urn_id: UrnId, nr_of_implementations: int, implementation: IMPLEMENTATION) -> bool:
        if nr_of_implementations > 0 and implementation == IMPLEMENTATION.IN_CODE:
            return True
        if nr_of_implementations == 0 and implementation == IMPLEMENTATION.NOT_APPLICABLE:
            return True
        if nr_of_implementations > 0 and implementation == IMPLEMENTATION.NOT_APPLICABLE:
            raise TypeError(f"Requirement {urn_id} should not have an implementation")
        return False

    def _get_test_stats(self, tests: List[TestData], svcs) -> TestStats:
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

    def _get_mvr_stats(self, mvrs, svcs) -> TestStats:
        if not mvrs:
            no_of_expected = sum(1 for svc in svcs if svc.verification in EXPECTS_MVRS)
            return TestStats(missing=no_of_expected)

        total = len(mvrs)
        passed = sum(1 for mvr in mvrs if mvr.passed)
        failed = total - passed
        return TestStats(total=total, passed=passed, failed=failed)

    def _get_annotated_automated_test_results_for_req(
        self,
        svcs_urn_ids: List[UrnId],
        all_svcs: Dict,
        annotations_tests: Dict[UrnId, List],
        automated_test_results: Dict[UrnId, List[TestData]],
    ) -> List[TestData]:
        results: List[TestData] = []
        for svc_uid in svcs_urn_ids:
            if svc_uid in annotations_tests:
                for ann in annotations_tests[svc_uid]:
                    test_urn_id = UrnId(urn=svc_uid.urn, id=ann.fully_qualified_name)
                    if test_urn_id in automated_test_results:
                        results.extend(automated_test_results[test_urn_id])
                    else:
                        results.append(TestData(fully_qualified_name=ann.fully_qualified_name, status=TEST_RUN_STATUS.MISSING))
            elif svc_uid in all_svcs and all_svcs[svc_uid].verification in EXPECTS_AUTOMATED_TESTS:
                results.append(TestData(fully_qualified_name="", status=TEST_RUN_STATUS.MISSING))
        return results

    def to_status_dict(self) -> dict:
        initial_urn = self._repo.get_initial_urn()
        filtered = self._repo.is_filtered()

        requirements = {}
        for urn_id, status in self._requirement_stats.items():
            requirements[str(urn_id)] = {
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
