# Copyright © LFV
import json

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.status.status import StatusCommand
from reqstool.locations.local_location import LocalLocation


@SVCs("SVC_021")
def test_status_incomplete_implementation(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )

    status, nr_of_incomplete_requirements = result.result

    assert nr_of_incomplete_requirements == 5


@SVCs("SVC_021")
def test_status_report_generation_sys_ms(local_testdata_resources_rootdir_w_path):
    result = StatusCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/empty_ms/ms-001"))
    )

    status, nr_of_incomplete_requirements = result.result

    assert nr_of_incomplete_requirements == 5


@SVCs("SVC_021")
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
