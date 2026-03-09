# Copyright © LFV


from reqstool.commands.status.statistics_container import (
    CombinedRequirementTestItem,
    StatisticsContainer,
    TestStatisticsItem,
    TotalStatisticsItem,
)
from reqstool.common.models.urn_id import UrnId
from reqstool.models.requirements import IMPLEMENTATION


def testtotal_statistics_item_update():
    stats_container = StatisticsContainer()
    stats_container.add_stats_for_requirement(
        req_urn_id=UrnId(urn="ms-101", id="REQ_101"),
        impls=1,
        completed=True,
        implementation=IMPLEMENTATION.IN_CODE,
        automated_tests_stats=TestStatisticsItem(
            nr_of_failed_tests=0,
            nr_of_missing_automated_tests=0,
            nr_of_missing_manual_tests=0,
            nr_of_skipped_tests=0,
            nr_of_passed_tests=1,
            nr_of_total_tests=1,
            not_applicable=False,
        ),
        mvrs_stats=TestStatisticsItem(
            nr_of_failed_tests=0,
            nr_of_missing_automated_tests=0,
            nr_of_missing_manual_tests=0,
            nr_of_skipped_tests=0,
            nr_of_passed_tests=0,
            nr_of_total_tests=0,
            not_applicable=True,
        ),
    )
    stats_container.total_statistics.nr_of_total_tests = 1
    stats_container.total_statistics.nr_of_passed_tests = 1

    expected = StatisticsContainer(
        requirement_statistics={
            UrnId(urn="ms-101", id="REQ_101"): CombinedRequirementTestItem(
                completed=True,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=1,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
            )
        },
        total_statistics=TotalStatisticsItem(
            nr_of_failed_tests=0,
            nr_of_missing_automated_tests=0,
            nr_of_missing_manual_tests=0,
            nr_of_skipped_tests=0,
            nr_of_passed_tests=1,
            nr_of_total_tests=1,
            nr_of_completed_requirements=1,
            nr_of_total_requirements=1,
            nr_of_reqs_with_implementation=1,
        ),
    )

    assert stats_container == expected
