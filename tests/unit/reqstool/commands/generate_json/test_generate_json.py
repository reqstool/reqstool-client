# Copyright © LFV

import json

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.generate_json.generate_json import GenerateJsonCommand
from reqstool.locations.local_location import LocalLocation


@SVCs("SVC_027")
def test_generate_json(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
    )
    assert gjc.result


def test_generate_json_no_filter_unchanged(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
    )
    result = json.loads(gjc.result)
    assert "ms-001:REQ_010" in result["requirements"]
    assert "ms-001:REQ_020" in result["requirements"]
    assert "ms-001:SVC_010" in result["svcs"]


def test_generate_json_filter_req_ids(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
        req_ids=["REQ_010"],
    )
    result = json.loads(gjc.result)

    # Only REQ_010 should be in requirements
    assert "ms-001:REQ_010" in result["requirements"]
    assert "ms-001:REQ_020" not in result["requirements"]

    # Related SVCs for REQ_010 should be included (SVC_010, SVC_021)
    assert "ms-001:SVC_010" in result["svcs"]
    assert "ms-001:SVC_021" in result["svcs"]

    # SVCs only related to REQ_020 should not be included
    assert "ms-001:SVC_022" not in result["svcs"]


def test_generate_json_filter_multiple_req_ids(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
        req_ids=["REQ_010", "REQ_020"],
    )
    result = json.loads(gjc.result)

    assert "ms-001:REQ_010" in result["requirements"]
    assert "ms-001:REQ_020" in result["requirements"]
    assert "ms-001:SVC_010" in result["svcs"]
    assert "ms-001:SVC_022" in result["svcs"]


def test_generate_json_filter_svc_ids(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
        svc_ids=["SVC_010"],
    )
    result = json.loads(gjc.result)

    # Only SVC_010 should be in svcs
    assert "ms-001:SVC_010" in result["svcs"]
    assert "ms-001:SVC_020" not in result["svcs"]
    assert "ms-001:SVC_022" not in result["svcs"]


def test_generate_json_filter_both(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
        req_ids=["REQ_010"],
        svc_ids=["SVC_022"],
    )
    result = json.loads(gjc.result)

    # REQ_010 from --req-ids
    assert "ms-001:REQ_010" in result["requirements"]
    # SVC_022 from --svc-ids
    assert "ms-001:SVC_022" in result["svcs"]
    # Related SVCs for REQ_010 should also be included
    assert "ms-001:SVC_010" in result["svcs"]


def test_generate_json_filter_no_match(local_testdata_resources_rootdir_w_path, caplog):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
        req_ids=["REQ_NONEXISTENT"],
    )
    result = json.loads(gjc.result)

    # No requirements should match
    assert len(result["requirements"]) == 0

    # Warning should be logged
    assert "REQ_NONEXISTENT" in caplog.text


def test_generate_json_filter_qualified_id(local_testdata_resources_rootdir_w_path):
    gjc = GenerateJsonCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        filter_data=True,
        req_ids=["ms-001:REQ_010"],
    )
    result = json.loads(gjc.result)

    assert "ms-001:REQ_010" in result["requirements"]
    assert "ms-001:REQ_020" not in result["requirements"]
