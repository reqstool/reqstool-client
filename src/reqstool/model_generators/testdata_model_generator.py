# Copyright © LFV

import logging
import os
import re
from pathlib import Path
from typing import Dict, List

from defusedxml import ElementTree as ET

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.models.urn_id import UrnId
from reqstool.models.test_data import TEST_RUN_STATUS, TestData, TestsData


def _status_priority(status: TEST_RUN_STATUS) -> int:
    return {TEST_RUN_STATUS.PASSED: 0, TEST_RUN_STATUS.SKIPPED: 1, TEST_RUN_STATUS.FAILED: 2}.get(status, 0)


class TestDataModelGenerator:
    UNIT_METHOD_IDENTIFIER_REGEX = r"^([a-zA-Z_$][a-zA-Z0-9_$]*).*$"
    KARATE_METHOD_IDENTIFIER_REGEX = r"\[\d+(?:\.\d+)?:\d+\]\s*(.+)"
    # Gradle parameterized: default "[N] args" or custom "{index} text" (N text) — method name absent
    DISPLAY_NAME_INDEX_REGEX = r"^\[?\d"

    def __init__(self, test_result_files: List[Path], urn: str):
        self.test_result_files = test_result_files
        self.urn = urn
        self.model: TestsData = self.__generate(test_result_files, urn)

    def __generate(self, test_result_files: List[Path], urn: str) -> TestsData:
        tests = self.__parse_test_data(test_result_files, urn)

        return TestsData(tests=tests)

    @Requirements("INGEST_0005", "INGEST_0006")
    def __parse_test_data(self, test_result_files: List[Path], urn: str) -> Dict[UrnId, TestData]:
        r_testdata: Dict[UrnId, TestData] = {}

        for test_result_file in test_result_files:

            if not os.path.isfile(test_result_file):
                logging.warning(f"test_result_file did not exist: {test_result_file}")
                continue

            tree = ET.parse(test_result_file)
            root = tree.getroot()

            for testcase in root.findall(".//testcase"):
                # Check if there is a match
                match_unit = re.match(self.UNIT_METHOD_IDENTIFIER_REGEX, testcase.attrib["name"])
                match_karate = re.match(self.KARATE_METHOD_IDENTIFIER_REGEX, testcase.attrib["name"])

                if match_unit:
                    methodname = match_unit.group(1)
                elif match_karate:
                    methodname = match_karate.group(1)
                elif re.match(self.DISPLAY_NAME_INDEX_REGEX, testcase.attrib["name"]):
                    logging.warning(
                        f"Skipping parameterized test case with display-name-only format "
                        f"(method name not recoverable): {testcase.attrib['name']!r} "
                        f"in {test_result_file}"
                    )
                    continue
                else:
                    logging.warning(
                        f"Skipping test case with unrecognized name format: "
                        f"{testcase.attrib['name']!r} in {test_result_file}"
                    )
                    continue

                test_run_status: TEST_RUN_STATUS

                if testcase.find("./failure") is not None:
                    test_run_status = TEST_RUN_STATUS.FAILED
                elif testcase.find("./skipped") is not None:
                    test_run_status = TEST_RUN_STATUS.SKIPPED
                else:
                    test_run_status = TEST_RUN_STATUS.PASSED

                fqn = f"{testcase.attrib['classname']}.{methodname}"

                test_data = TestData(fully_qualified_name=fqn, status=test_run_status)
                urn_id = UrnId(urn=urn, id=fqn)
                existing = r_testdata.get(urn_id)
                if existing is None or _status_priority(test_run_status) > _status_priority(existing.status):
                    r_testdata[urn_id] = test_data

        return r_testdata
