# Copyright © LFV

import logging
import re

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.models.urn_id import UrnId
from reqstool.model_generators.testdata_model_generator import TestDataModelGenerator
from reqstool.models.test_data import TEST_RUN_STATUS

karate_method_names = [
    "[1.4:55] Create a subscripiton with filter and receive messages",
    "[1:38] Create a subscripiton with filter and receive messages",
    "[1.2:53] Create a subscripiton with filter and receive messages",
]

unit_method_names = [
    "testFlightIdAircraftId",
    "testFlightIdAircraftId(String, int)[1]",
]


@SVCs("SVC_006")
@pytest.mark.parametrize("method_name", karate_method_names)
def test_karate_method_identifier_regex(method_name):
    karate_match = re.match(TestDataModelGenerator.KARATE_METHOD_IDENTIFIER_REGEX, method_name)
    assert karate_match is not None
    assert karate_match.group(1) == "Create a subscripiton with filter and receive messages"


@SVCs("SVC_007")
@pytest.mark.parametrize("method_name", unit_method_names)
def test_unit_method_identifier_regex(method_name):
    unit_match = re.match(TestDataModelGenerator.UNIT_METHOD_IDENTIFIER_REGEX, method_name)
    assert unit_match is not None
    assert unit_match.group(1) == "testFlightIdAircraftId"


display_name_index_names = [
    "[1] ACTIVE",
    "[2] conflictMessage=Entry 10 is AWAITING_MANUAL_EDIT, expected PENDING",
    "1 status=ACTIVE",
    "2 someDisplayName",
]


@pytest.mark.parametrize("method_name", display_name_index_names)
def test_display_name_index_regex(method_name):
    assert re.match(TestDataModelGenerator.UNIT_METHOD_IDENTIFIER_REGEX, method_name) is None
    assert re.match(TestDataModelGenerator.KARATE_METHOD_IDENTIFIER_REGEX, method_name) is None
    assert re.match(TestDataModelGenerator.DISPLAY_NAME_INDEX_REGEX, method_name) is not None


def test_parameterized_testdata_model_generator(resource_funcname_rootdir_w_path, caplog):
    with caplog.at_level(logging.WARNING):
        tdmg = TestDataModelGenerator(
            test_result_files=[
                resource_funcname_rootdir_w_path("TEST-com.example.StatusServiceTest.xml")
            ],
            urn="test",
        )

    tests = tdmg.model.tests

    # Only the Maven-style method is in the index; Gradle display-name entries are skipped
    assert len(tests) == 1

    # checkStatusMaven: [1] PASSED, [2] PASSED, [3] FAILED → worst-status-wins → FAILED
    fqn = "com.example.StatusServiceTest.checkStatusMaven"
    urn_id = UrnId(urn="test", id=fqn)
    assert urn_id in tests
    assert tests[urn_id].status == TEST_RUN_STATUS.FAILED

    # Gradle display-name entries produced warnings, not errors
    assert any("display-name-only" in r.message for r in caplog.records)
    assert all(r.levelname != "ERROR" for r in caplog.records)


def test_testdata_model_generator(local_testdata_resources_rootdir_w_path):
    # TODO:
    # * Test the different variants: passed, skipped, failure etc
    # * Test different types of file structure (Java, Python, Frontend Typescript)

    tdmg = (
        TestDataModelGenerator(
            test_result_files=[
                local_testdata_resources_rootdir_w_path(
                    "test_basic/baseline/ms-101/test_results/failsafe/TEST-com.example.RequirementsExampleTestsIT.xml"
                ),
                local_testdata_resources_rootdir_w_path(
                    "test_basic/baseline/ms-101/test_results/surefire/TEST-com.example.RequirementsExampleTests.xml"
                ),
            ],
            urn="test",
        ),
    )

    assert tdmg is not None
