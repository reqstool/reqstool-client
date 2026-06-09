# Copyright © LFV
import json

import pytest

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.status.status import StatusCommand
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository


@SVCs("SVC_STATUS_0001")
def test_status_incomplete_implementation(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )

    status, nr_of_incomplete_requirements = result.result

    assert nr_of_incomplete_requirements == 5


@SVCs("SVC_STATUS_0001")
def test_status_report_generation_sys_ms(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/empty_ms/ms-001"))
    )

    status, nr_of_incomplete_requirements = result.result

    assert nr_of_incomplete_requirements == 5


@SVCs("SVC_STATUS_0005")
def test_status_json_format(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        format="json",
    )

    status, nr_of_incomplete_requirements = result.result

    data = json.loads(status)
    assert "metadata" in data
    assert "requirements" in data
    assert "totals" in data

    ts = data["totals"]
    assert "requirements" in ts
    assert ts["requirements"]["total"] > 0
    assert "completed" in ts["requirements"]

    # Verify requirements keys are urn:id strings
    for key in data["requirements"]:
        assert ":" in key

    # Verify enum serialization uses values
    for req_stats in data["requirements"].values():
        assert req_stats["implementation_type"] in ["in-code", "N/A"]

    assert nr_of_incomplete_requirements == 5


def _inject_post_tests(db, urn, paths):
    # Reach the name-mangled static helper that performs the injection.
    return StatusCommand._StatusCommand__inject_post_tests(db, urn, paths)


@SVCs("SVC_STATUS_0008")
def test_with_post_tests_incorporates_junit_outcomes(local_testdata_resources_rootdir_w_path):
    """STATUS_0008: outcomes from a post-build JUnit XML file are inserted into the status DB."""
    db = RequirementsDatabase()
    CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        database=db,
    )
    repo = RequirementsRepository(db)
    junit = local_testdata_resources_rootdir_w_path(
        "test_basic/no_impls/basic/ms-101/test_results/surefire/TEST-com.example.RequirementsExampleTests.xml"
    )

    _inject_post_tests(db, repo.get_initial_urn(), [str(junit)])

    fqns = [row["fqn"] for row in db.connection.execute("SELECT fqn FROM test_results").fetchall()]
    assert any("RequirementsExampleTests" in fqn for fqn in fqns)
    db.close()


@SVCs("SVC_STATUS_0008")
def test_with_post_tests_missing_file_raises(local_testdata_resources_rootdir_w_path):
    """STATUS_0008: a non-existent post-build file is rejected up-front."""
    with pytest.raises(FileNotFoundError):
        StatusCommand(
            location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
            with_post_tests=["/nonexistent/post-tests.xml"],
        )
