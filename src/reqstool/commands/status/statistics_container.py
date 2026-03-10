# Copyright © LFV

from pydantic import BaseModel, ConfigDict, Field

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.models.urn_id import UrnId
from reqstool.models.requirements import IMPLEMENTATION


@Requirements("REQ_028")
class TestStatisticsItem(BaseModel):
    nr_of_failed_tests: int = 0
    nr_of_missing_automated_tests: int = 0
    nr_of_missing_manual_tests: int = 0
    nr_of_skipped_tests: int = 0
    nr_of_passed_tests: int = 0
    nr_of_total_tests: int = 0
    not_applicable: bool = False

    def is_completed(self) -> bool:
        if self.nr_of_missing_automated_tests or self.nr_of_missing_manual_tests > 0:
            return False
        return self.nr_of_total_tests == self.nr_of_passed_tests


@Requirements("REQ_028")
class CombinedRequirementTestItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    completed: bool = False
    nr_of_implementations: int = 0
    automated_tests_stats: TestStatisticsItem = Field(default_factory=TestStatisticsItem)
    mvrs_stats: TestStatisticsItem = Field(default_factory=TestStatisticsItem)
    implementation: IMPLEMENTATION = IMPLEMENTATION.IN_CODE


@Requirements("REQ_028")
class TotalStatisticsItem(BaseModel):
    nr_of_failed_tests: int = 0
    nr_of_missing_automated_tests: int = 0
    nr_of_missing_manual_tests: int = 0
    nr_of_skipped_tests: int = 0
    nr_of_passed_tests: int = 0
    nr_of_total_tests: int = 0
    nr_of_completed_requirements: int = 0
    nr_of_total_requirements: int = 0
    nr_of_reqs_with_implementation: int = 0
    nr_of_total_svcs: int = 0
    nr_of_completed_reqs_no_implementation: int = 0
    nr_of_total_reqs_no_implementation: int = 0
    nr_of_total_manual_tests: int = 0
    nr_of_total_annotated_tests: int = 0
    nr_of_passed_manual_tests: int = 0
    nr_of_failed_manual_tests: int = 0
    nr_of_passed_automatic_tests: int = 0
    nr_of_failed_automatic_tests: int = 0

    def update(self, completed: bool, combined_req_test_item: CombinedRequirementTestItem) -> None:
        self.nr_of_total_requirements += 1
        self.nr_of_missing_automated_tests += combined_req_test_item.automated_tests_stats.nr_of_missing_automated_tests
        self.nr_of_missing_manual_tests += combined_req_test_item.mvrs_stats.nr_of_missing_manual_tests
        if combined_req_test_item.nr_of_implementations > 0:
            self.nr_of_reqs_with_implementation += 1

        # Some requirements could be completed without any implementation
        if completed and combined_req_test_item.implementation == IMPLEMENTATION.NOT_APPLICABLE:
            self.nr_of_completed_reqs_no_implementation += 1

        if combined_req_test_item.implementation == IMPLEMENTATION.NOT_APPLICABLE:
            self.nr_of_total_reqs_no_implementation += 1

        if completed:
            self.nr_of_completed_requirements += 1


@Requirements("REQ_028")
class StatisticsContainer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirement_statistics: dict[UrnId, CombinedRequirementTestItem] = Field(default_factory=dict)

    total_statistics: TotalStatisticsItem = Field(default_factory=TotalStatisticsItem)

    def add_stats_for_requirement(
        self,
        req_urn_id: UrnId,
        impls: int,
        completed: bool,
        implementation: IMPLEMENTATION,
        automated_tests_stats: TestStatisticsItem,
        mvrs_stats: TestStatisticsItem,
    ) -> None:
        assert id not in self.requirement_statistics

        combined_requirement_test_item = CombinedRequirementTestItem(
            completed=completed,
            nr_of_implementations=impls,
            automated_tests_stats=automated_tests_stats,
            mvrs_stats=mvrs_stats,
            implementation=implementation,
        )

        self.requirement_statistics[req_urn_id] = combined_requirement_test_item

        self.total_statistics.update(completed=completed, combined_req_test_item=combined_requirement_test_item)
