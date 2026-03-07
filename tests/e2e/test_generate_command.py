# Copyright © LFV

import json
import os
import subprocess

import pytest

TESTDATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "test_data", "data", "local", "test_standard", "baseline", "ms-001"
)


def _run_reqstool(*args):
    result = subprocess.run(
        ["hatch", "run", "dev:reqstool", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result


@pytest.mark.e2e
def test_export_no_filters_returns_all_data():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:REQ_010" in data["requirements"]
    assert "ms-001:REQ_020" in data["requirements"]
    assert "ms-001:SVC_010" in data["svcs"]
    assert "ms-001:SVC_020" in data["svcs"]


@pytest.mark.e2e
def test_export_single_req_id():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--req-ids", "REQ_010")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:REQ_010" in data["requirements"]
    assert "ms-001:REQ_020" not in data["requirements"]
    # Related SVCs for REQ_010
    assert "ms-001:SVC_010" in data["svcs"]
    assert "ms-001:SVC_021" in data["svcs"]


@pytest.mark.e2e
def test_export_multiple_req_ids():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--req-ids", "REQ_010", "REQ_020")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:REQ_010" in data["requirements"]
    assert "ms-001:REQ_020" in data["requirements"]


@pytest.mark.e2e
def test_export_single_svc_id():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--svc-ids", "SVC_010")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:SVC_010" in data["svcs"]
    assert "ms-001:SVC_020" not in data["svcs"]


@pytest.mark.e2e
def test_export_multiple_svc_ids():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--svc-ids", "SVC_010", "SVC_020")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:SVC_010" in data["svcs"]
    assert "ms-001:SVC_020" in data["svcs"]


@pytest.mark.e2e
def test_export_both_req_and_svc_ids():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--req-ids", "REQ_010", "--svc-ids", "SVC_022")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:REQ_010" in data["requirements"]
    assert "ms-001:SVC_022" in data["svcs"]
    # Related SVCs from REQ_010 also included
    assert "ms-001:SVC_010" in data["svcs"]


@pytest.mark.e2e
def test_export_nonexistent_id_warns():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--req-ids", "REQ_NONEXISTENT")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data["requirements"]) == 0
    assert "REQ_NONEXISTENT" in result.stderr


@pytest.mark.e2e
def test_generate_json_deprecated():
    result = _run_reqstool("generate-json", "local", "-p", TESTDATA_PATH)
    assert result.returncode == 0
    assert "deprecated" in result.stderr.lower()
    data = json.loads(result.stdout)
    assert "ms-001:REQ_010" in data["requirements"]


@pytest.mark.e2e
def test_export_format_json_explicit():
    result = _run_reqstool("export", "--format", "json", "local", "-p", TESTDATA_PATH)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "requirements" in data


@pytest.mark.e2e
def test_export_requirement_ids_alias():
    result = _run_reqstool("export", "local", "-p", TESTDATA_PATH, "--requirement-ids", "REQ_010")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ms-001:REQ_010" in data["requirements"]
    assert "ms-001:REQ_020" not in data["requirements"]
