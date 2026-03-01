# Copyright © LFV

from enum import Enum
from typing import Dict, List, Sequence

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.commands.status.statistics_container import StatisticsContainer, TestStatisticsItem
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import IMPLEMENTATION
from reqstool.models.svcs import VERIFICATIONTYPES, SVCData
from reqstool.models.test_data import TEST_RUN_STATUS, TestData

EXPECTS_MVRS = [
    VERIFICATIONTYPES.MANUAL_TEST,
    VERIFICATIONTYPES.REVIEW,
    VERIFICATIONTYPES.PLATFORM,
    VERIFICATIONTYPES.OTHER,
]
EXPECTS_AUTOMATED_TESTS = [VERIFICATIONTYPES.AUTOMATED_TEST]


class StatsTestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    MISSING = "missing"
    NA = "N/A"


@Requirements("REQ_028")
class StatisticsGenerator:
    def __init__(
        self, initial_location: LocationInterface, semantic_validator: SemanticValidator, apply_filter: bool = True
    ):
        self.cid: CombinedIndexedDataset = self._get_combined_index_data(
            initial_location=initial_location, semantic_validator=semantic_validator, apply_filter=apply_filter
        )
        self.stats_container = self.calculate_totals()
        self.result: StatisticsContainer = self._calculate(self.cid)

    def _get_combined_index_data(
        self, initial_location: LocationInterface, semantic_validator: SemanticValidator, apply_filter: bool
    ) -> CombinedIndexedDataset:
        crd = CombinedRawDatasetsGenerator(
            initial_location=initial_location, semantic_validator=semantic_validator
        ).combined_raw_datasets
        cid: CombinedIndexedDataset = CombinedIndexedDatasetGenerator(
            _crd=crd, _filtered=apply_filter
        ).combined_indexed_dataset

        return cid

    def _calculate(self, cid: CombinedIndexedDataset) -> StatisticsContainer:
        for urn_id in cid.requirements.keys():
            # Get all svc UrnIds related to current requirement
            svcs_urn_ids: List[UrnId] = self._get_urn_ids_for_svcs(
                urn_id=urn_id, svcs_from_req=cid.svcs_from_req.items()
            )

            # Get svcs for current requirement
            svcs: List[SVCData] = [cid.svcs[urn_id] for urn_id in svcs_urn_ids]

            # Check if current requirement should have mvrs and/or automated tests
            should_have_mvrs = self._req_verification_equals(svcs=svcs, verification=EXPECTS_MVRS)
            should_have_automated_tests = self._req_verification_equals(svcs=svcs, verification=EXPECTS_AUTOMATED_TESTS)

            # Get no of implementations for current requirement
            nr_of_implementations = self._get_nr_of_impls_for_req(urn_id=urn_id)

            mvr_ids: List[UrnId] = self._get_mvr_ids_for_req(svcs_urn_ids=svcs_urn_ids)

            # Get mvrs for current requirement if there are any (else None)
            mvrs: List[MVRData] | None = self._get_mvrs_for_req(mvrs=cid.mvrs, mvr_ids=mvr_ids)

            # If there should be mvr results, then get the results
            mvr_stats: TestStatisticsItem = (
                self._get_mvr_stats(mvrs=mvrs, svcs=svcs)
                if should_have_mvrs
                else TestStatisticsItem(not_applicable=True)
            )

            # get test data for all tests related to current requirement
            automated_test_results: List[TestData] = self._get_annotated_automated_test_results_for_req(
                svcs_urn_ids=svcs_urn_ids
            )
            # get statistics for the automated tests
            automated_test_stats = (
                self._get_test_stats(tests=automated_test_results, svcs=svcs)
                if should_have_automated_tests
                else TestStatisticsItem(not_applicable=True)
            )

            completed = (
                self._check_implementation(urn_id=urn_id, nr_of_implementations=nr_of_implementations)
                and mvr_stats.is_completed()
                and automated_test_stats.is_completed()
                and (should_have_mvrs or should_have_automated_tests)
            )

            self.stats_container.add_stats_for_requirement(
                req_urn_id=urn_id,
                impls=nr_of_implementations,
                completed=completed,
                automated_tests_stats=automated_test_stats,
                mvrs_stats=mvr_stats,
                implementation=self.cid.requirements[urn_id].implementation,
            )

        return self.stats_container

    def _get_urn_ids_for_svcs(self, urn_id: UrnId, svcs_from_req: Dict[UrnId, List[UrnId]]) -> List[UrnId]:
        svcs_urn_ids: List[UrnId] = []
        for req_urn_id, svc_list in svcs_from_req:
            if urn_id == req_urn_id:
                for svc in svc_list:
                    svcs_urn_ids.append(svc)
        return svcs_urn_ids

    def _check_implementation(self, urn_id: UrnId, nr_of_implementations: int) -> bool:
        implementation = self.cid.requirements[urn_id].implementation
        implementation_ok = False
        if (
            nr_of_implementations > 0
            and implementation == IMPLEMENTATION.IN_CODE
            or nr_of_implementations == 0
            and implementation == IMPLEMENTATION.NOT_APPLICABLE
        ):
            implementation_ok = True
        elif nr_of_implementations > 0 and implementation == IMPLEMENTATION.NOT_APPLICABLE:
            # Throw error if there are implementations of a requirement that does not expect it
            raise TypeError(f"Requirement {urn_id} should not have an implementation")

        return implementation_ok

    # Returns a string if all test passes or fails
    def _get_test_stats(self, tests: List[TestData], svcs: List[SVCData]) -> TestStatisticsItem:
        if not tests:
            # if we have no results from the gathering of results, expect at least as many missing
            # tests as we have svc's
            no_of_missing_automated_tests = sum(1 for svc in svcs if svc.verification in EXPECTS_AUTOMATED_TESTS)
            return TestStatisticsItem(nr_of_missing_automated_tests=no_of_missing_automated_tests)

        stats_item = TestStatisticsItem(nr_of_total_tests=len(tests))
        # we need to do a check if the current automated test is already counted as passed or failed,
        # as each test could relate to several svc's
        for test in tests:
            if test.fully_qualified_name == "":
                stats_item.nr_of_total_tests -= 1
            match (test.status):
                case TEST_RUN_STATUS.PASSED:
                    stats_item.nr_of_passed_tests += 1
                case TEST_RUN_STATUS.FAILED:
                    stats_item.nr_of_failed_tests += 1
                case TEST_RUN_STATUS.SKIPPED:
                    stats_item.nr_of_skipped_tests += 1
                case TEST_RUN_STATUS.MISSING:
                    stats_item.nr_of_missing_automated_tests += 1

        return stats_item

    # Returns a string if all mvrs passes or fails
    def _get_mvr_stats(self, mvrs: List[MVRData], svcs: List[SVCData]) -> TestStatisticsItem:
        # svc specifies mvr, but no mvr exists
        if not mvrs:
            # we need to know how many mvr results that are expected in order to display statistics correctly,
            #  if the mvrs variable is None and we expect mvrs, go through svcs and count how many there are defined
            # for this req with expected verification status
            no_of_expected_mvrs = sum(1 for svc in svcs if svc.verification in EXPECTS_MVRS)

            return TestStatisticsItem(nr_of_missing_manual_tests=no_of_expected_mvrs)

        stats_item = TestStatisticsItem(nr_of_total_tests=len(mvrs))

        for mvr in mvrs:
            if mvr.passed:
                stats_item.nr_of_passed_tests += 1
            else:
                stats_item.nr_of_failed_tests += 1

        return stats_item

    def _req_verification_equals(self, svcs: List[SVCData], verification: Sequence[VERIFICATIONTYPES]) -> bool:
        for svc in svcs:
            if svc.verification in verification:
                return True
        return False

    # Get the nr of impls for current requirement
    def _get_nr_of_impls_for_req(self, urn_id: UrnId) -> int:
        nr_of_implementations = 0
        for annotation_id in self.cid.annotations_impls.keys():
            if annotation_id == urn_id:
                nr_of_implementations += 1
        return nr_of_implementations

    def _get_annotated_automated_test_results_for_req(
        self,
        svcs_urn_ids: List[UrnId],
    ) -> List[TestData]:
        automated_test_results: List[TestData] = []
        for urn_id in svcs_urn_ids:
            if urn_id in self.cid.annotations_tests:
                annotations = self.cid.annotations_tests[urn_id]
                for tests in annotations:
                    for test in tests:
                        test_urn_id = UrnId(urn=urn_id.urn, id=test.fully_qualified_name)
                        results = self.__get_annotated_test_results(urn_id=test_urn_id)
                        automated_test_results.extend(results)
            else:
                # No tests found for this SVC - create TestData with missing status
                automated_test_results.append(TestData(fully_qualified_name="", status=TEST_RUN_STATUS.MISSING))

        return automated_test_results

    def _get_automated_test_results_for_req(
        self, automated_test_fqn: List[str], automated_test_result: Dict[UrnId, List[TestData]]
    ) -> List[TEST_RUN_STATUS]:
        test_results: List[TEST_RUN_STATUS] = []
        for fqn in automated_test_fqn:
            for test_id, test_result in automated_test_result:
                if test_id.id == fqn:
                    for test in test_result:
                        test_results.append(test)
        return test_results

    def _get_mvr_ids_for_req(self, svcs_urn_ids: List[UrnId]) -> List[UrnId]:
        mvr_ids: List[UrnId] = []
        for svc_urn_id in svcs_urn_ids:
            for id, value in self.cid.mvrs_from_svc.items():
                if id == svc_urn_id:
                    for urn in value:
                        mvr_ids.append(urn)
        return mvr_ids

    def _get_mvrs_for_req(self, mvrs: Dict[UrnId, MVRData], mvr_ids: List[UrnId]) -> List[MVRData] | None:
        return [mvrs[mvr_id] for mvr_id in mvr_ids] if mvr_ids else None

    def calculate_totals(self) -> StatisticsContainer:
        stats_container = StatisticsContainer()
        # Sum totals
        total_no_of_annotated_tests = len(self.cid.automated_test_result)

        # Total mvrs
        total_no_of_mvrs = len(self.cid.mvrs)

        # Total SVCs
        stats_container._total_statistics.nr_of_total_svcs = len(self.cid.svcs)

        # Total manual tests
        stats_container._total_statistics.nr_of_total_manual_tests = total_no_of_mvrs

        # Total annotated tests
        stats_container._total_statistics.nr_of_total_annotated_tests = total_no_of_annotated_tests

        # Combined
        stats_container._total_statistics.nr_of_total_tests = total_no_of_annotated_tests + total_no_of_mvrs

        # count status of each test
        # start with mvrs
        self.__count_mvr_status(mvrs=self.cid.mvrs.values(), stats_container=stats_container)

        # then annotated automated tests
        automated_test_results: List[str] = self.__get_results_from_annotated_tests()
        # sum up test statistics
        self.__calculate_total_automated_test_statistics(
            test_results=automated_test_results, stats_container=stats_container
        )

        return stats_container

    def __count_mvr_status(self, mvrs: List[MVRData], stats_container: StatisticsContainer) -> None:
        for mvr in mvrs:
            if mvr.passed:
                stats_container._total_statistics.nr_of_passed_tests += 1
                stats_container._total_statistics.nr_of_passed_manual_tests += 1

            else:
                stats_container._total_statistics.nr_of_failed_tests += 1
                stats_container._total_statistics.nr_of_failed_manual_tests += 1

    def __get_results_from_annotated_tests(self) -> List[TEST_RUN_STATUS]:
        test_results: List[TEST_RUN_STATUS] = []
        parsed_test_annotation_urns: List[UrnId] = []
        for urn_id, annotation_data in self.cid.annotations_tests.items():
            for annotation_test in annotation_data:
                for test in annotation_test:
                    urn_id = UrnId(urn=urn_id.urn, id=test.fully_qualified_name)
                    # we should save this urn_id in a list, and only do the result lookup
                    # below if the urn_id is not in list.
                    # This is to avoid duplicate counting of the total test results
                    if urn_id not in parsed_test_annotation_urns:
                        parsed_test_annotation_urns.append(urn_id)
                        results = self.__get_annotated_test_results(urn_id=urn_id)
                        test_results.extend(results)
        return test_results

    def __get_annotated_test_results(self, urn_id: UrnId) -> List[TEST_RUN_STATUS]:
        test_results: List[TEST_RUN_STATUS] = []
        # do lookup for each test from previous method, and if result is missing, add a Missing status
        if urn_id in self.cid.automated_test_result:
            tests = self.cid.automated_test_result[urn_id]
            for test in tests:
                # We shouldn't add the same test result several times.
                if test not in test_results:
                    test_results.append(test)

        return test_results

    def __calculate_total_automated_test_statistics(
        self, test_results: List[TEST_RUN_STATUS], stats_container: StatisticsContainer
    ) -> None:
        for test in test_results:
            match test.status:
                case TEST_RUN_STATUS.PASSED:
                    stats_container._total_statistics.nr_of_passed_tests += 1
                    stats_container._total_statistics.nr_of_passed_automatic_tests += 1
                case TEST_RUN_STATUS.FAILED:
                    stats_container._total_statistics.nr_of_failed_tests += 1
                    stats_container._total_statistics.nr_of_failed_automatic_tests += 1
                case TEST_RUN_STATUS.SKIPPED:
                    stats_container._total_statistics.nr_of_skipped_tests += 1
                case TEST_RUN_STATUS.MISSING:
                    stats_container._total_statistics.nr_of_missing_automated_tests += 1
                    stats_container._total_statistics.nr_of_total_tests -= 1
