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
    assert "requirement_statistics" in data
    assert "total_statistics" in data

    ts = data["total_statistics"]
    assert "nr_of_total_requirements" in ts
    assert "nr_of_completed_requirements" in ts

    # Verify requirement_statistics keys are urn:id strings
    for key in data["requirement_statistics"]:
        assert ":" in key

    # Verify enum serialization uses values
    for req_stats in data["requirement_statistics"].values():
        assert req_stats["implementation"] in ["in-code", "N/A"]

    assert nr_of_incomplete_requirements == 5
