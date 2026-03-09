# Copyright © LFV

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.status.statistics_container import (
    CombinedRequirementTestItem,
    StatisticsContainer,
    TestStatisticsItem,
    TotalStatisticsItem,
)
from reqstool.commands.status.statistics_generator import StatisticsGenerator
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.models.requirements import IMPLEMENTATION


@SVCs("SVC_022")
def test_calculate_test_basic(local_testdata_resources_rootdir_w_path):
    result: StatisticsContainer = StatisticsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    ).result

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
            ),
            UrnId(urn="ms-101", id="REQ_102"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=0,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
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
            ),
            UrnId(urn="ms-101", id="REQ_201"): CombinedRequirementTestItem(
                completed=True,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=1,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ms-101", id="REQ_202"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=0,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
        },
        total_statistics=TotalStatisticsItem(
            nr_of_failed_tests=2,
            nr_of_missing_automated_tests=0,
            nr_of_missing_manual_tests=0,
            nr_of_skipped_tests=0,
            nr_of_passed_tests=2,
            nr_of_total_tests=4,
            nr_of_completed_requirements=2,
            nr_of_total_requirements=4,
            nr_of_reqs_with_implementation=2,
            nr_of_total_svcs=4,
            nr_of_completed_reqs_no_implementation=0,
            nr_of_total_reqs_no_implementation=0,
            nr_of_total_manual_tests=2,
            nr_of_total_annotated_tests=2,
            nr_of_passed_manual_tests=1,
            nr_of_failed_manual_tests=1,
            nr_of_passed_automatic_tests=1,
            nr_of_failed_automatic_tests=1,
        ),
    )
    assert result == expected


@SVCs("SVC_023")
def test_calculate_test_standard_ms001(local_testdata_resources_rootdir_w_path):
    result: StatisticsContainer = StatisticsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    ).result

    expected = StatisticsContainer(
        requirement_statistics={
            UrnId(urn="ms-001", id="REQ_010"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=2,
                    nr_of_total_tests=3,
                    not_applicable=False,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ms-001", id="REQ_020"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
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
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="sys-001", id="REQ_sys001_505"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=0,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=1,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=1,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ext-001", id="REQ_ext001_100"): CombinedRequirementTestItem(
                completed=True,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ext-002", id="REQ_ext002_300"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=1,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
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
            ),
            UrnId(urn="ext-002", id="REQ_ext002_400"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
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
                    nr_of_missing_manual_tests=1,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=False,
                ),
            ),
        },
        total_statistics=TotalStatisticsItem(
            nr_of_completed_reqs_no_implementation=0,
            nr_of_completed_requirements=1,
            nr_of_failed_automatic_tests=1,
            nr_of_failed_manual_tests=1,
            nr_of_failed_tests=2,
            nr_of_missing_automated_tests=2,
            nr_of_missing_manual_tests=2,
            nr_of_passed_automatic_tests=4,
            nr_of_passed_manual_tests=1,
            nr_of_passed_tests=5,
            nr_of_reqs_with_implementation=10,
            nr_of_skipped_tests=0,
            nr_of_total_annotated_tests=5,
            nr_of_total_manual_tests=2,
            nr_of_total_reqs_no_implementation=0,
            nr_of_total_requirements=6,
            nr_of_total_svcs=9,
            nr_of_total_tests=7,
        ),
    )
    assert result == expected


@SVCs("SVC_024")
def test_calculate_empty_standard_ms001(local_testdata_resources_rootdir_w_path):
    result: StatisticsContainer = StatisticsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/empty_ms/ms-001")),
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    ).result

    expected = StatisticsContainer(
        requirement_statistics={
            UrnId(urn="sys-001", id="REQ_sys001_505"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=0,
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
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="sys-001", id="REQ_sys001_010"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=2,
                    nr_of_total_tests=3,
                    not_applicable=False,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="sys-001", id="REQ_sys001_020"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
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
                    nr_of_missing_manual_tests=1,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ext-001", id="REQ_ext001_100"): CombinedRequirementTestItem(
                completed=True,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ext-002", id="REQ_ext002_300"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=1,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
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
            ),
            UrnId(urn="ext-002", id="REQ_ext002_400"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=2,
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
                    nr_of_missing_manual_tests=1,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=False,
                ),
            ),
        },
        total_statistics=TotalStatisticsItem(
            nr_of_failed_tests=2,
            nr_of_missing_automated_tests=1,
            nr_of_missing_manual_tests=2,
            nr_of_skipped_tests=0,
            nr_of_passed_tests=5,
            nr_of_total_tests=7,
            nr_of_completed_requirements=1,
            nr_of_total_requirements=6,
            nr_of_reqs_with_implementation=10,
            nr_of_total_svcs=8,
            nr_of_completed_reqs_no_implementation=0,
            nr_of_total_reqs_no_implementation=0,
            nr_of_total_manual_tests=2,
            nr_of_total_annotated_tests=5,
            nr_of_passed_manual_tests=1,
            nr_of_failed_manual_tests=1,
            nr_of_passed_automatic_tests=4,
            nr_of_failed_automatic_tests=1,
        ),
    )
    assert result == expected


@SVCs("SVC_037")
def test_calculate_test_basic_no_impls(local_testdata_resources_rootdir_w_path):
    result: StatisticsContainer = StatisticsGenerator(
        initial_location=LocalLocation(
            path=local_testdata_resources_rootdir_w_path("test_basic/no_impls/basic/ms-101")
        ),
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    ).result

    expected = StatisticsContainer(
        requirement_statistics={
            UrnId(urn="ms-101", id="REQ_101"): CombinedRequirementTestItem(
                completed=True,
                implementation=IMPLEMENTATION.NOT_APPLICABLE,
                nr_of_implementations=0,
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
            ),
            UrnId(urn="ms-101", id="REQ_201"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.IN_CODE,
                nr_of_implementations=1,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ms-101", id="REQ_1337"): CombinedRequirementTestItem(
                completed=True,
                implementation=IMPLEMENTATION.NOT_APPLICABLE,
                nr_of_implementations=0,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=1,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
            UrnId(urn="ms-101", id="REQ_1339"): CombinedRequirementTestItem(
                completed=False,
                implementation=IMPLEMENTATION.NOT_APPLICABLE,
                nr_of_implementations=0,
                automated_tests_stats=TestStatisticsItem(
                    nr_of_failed_tests=0,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=0,
                    not_applicable=True,
                ),
                mvrs_stats=TestStatisticsItem(
                    nr_of_failed_tests=1,
                    nr_of_missing_automated_tests=0,
                    nr_of_missing_manual_tests=0,
                    nr_of_skipped_tests=0,
                    nr_of_passed_tests=0,
                    nr_of_total_tests=1,
                    not_applicable=False,
                ),
            ),
        },
        total_statistics=TotalStatisticsItem(
            nr_of_completed_requirements=2,
            nr_of_failed_tests=2,
            nr_of_missing_automated_tests=0,
            nr_of_missing_manual_tests=0,
            nr_of_passed_tests=2,
            nr_of_completed_reqs_no_implementation=2,
            nr_of_total_reqs_no_implementation=3,
            nr_of_reqs_with_implementation=1,
            nr_of_skipped_tests=0,
            nr_of_total_requirements=4,
            nr_of_total_svcs=4,
            nr_of_total_tests=4,
            nr_of_total_manual_tests=3,
            nr_of_total_annotated_tests=1,
            nr_of_passed_manual_tests=1,
            nr_of_failed_manual_tests=2,
            nr_of_passed_automatic_tests=1,
            nr_of_failed_automatic_tests=0,
        ),
    )
    assert result == expected


def test_raise_error_on_requirement_with_implementation_when_not_expected(local_testdata_resources_rootdir_w_path):

    with pytest.raises(TypeError):
        StatisticsGenerator(
            initial_location=LocalLocation(
                path=local_testdata_resources_rootdir_w_path("test_basic/no_impls/with_error/ms-101")
            ),
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        )
