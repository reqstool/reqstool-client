import json
from importlib.resources import files

import jsonschema
import pytest

import reqstool.resources.schemas.v1


def _load_schema(name: str) -> dict:
    return json.loads(files(reqstool.resources.schemas.v1).joinpath(name).read_text())


@pytest.fixture
def status_schema():
    return _load_schema("status_output.schema.json")


@pytest.fixture
def export_schema():
    return _load_schema("export_output.schema.json")


# ── Meta-schema validation ────────────────────────────────────────────────────


def test_status_schema_is_valid_json_schema(status_schema):
    jsonschema.Draft202012Validator.check_schema(status_schema)


def test_export_schema_is_valid_json_schema(export_schema):
    jsonschema.Draft202012Validator.check_schema(export_schema)


# ── Status schema: positive cases ─────────────────────────────────────────────

MINIMAL_STATUS = {
    "metadata": {"initial_urn": "ms-001", "filtered": False},
    "requirements": {},
    "totals": {
        "requirements": {
            "total": 0,
            "completed": 0,
            "with_implementation": 0,
            "without_implementation": {"total": 0, "completed": 0},
        },
        "svcs": {"total": 0},
        "tests": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "missing_automated": 0, "missing_manual": 0},
        "automated_tests": {"total": 0, "passed": 0, "failed": 0},
        "manual_tests": {"total": 0, "passed": 0, "failed": 0},
    },
}

FULL_STATUS = {
    "metadata": {"initial_urn": "ms-001", "filtered": True},
    "requirements": {
        "ms-001:REQ_010": {
            "completed": True,
            "implementations": 2,
            "implementation_type": "in-code",
            "automated_tests": {
                "total": 3,
                "passed": 3,
                "failed": 0,
                "skipped": 0,
                "missing": 0,
                "not_applicable": False,
            },
            "manual_tests": {
                "total": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "missing": 0,
                "not_applicable": False,
            },
        },
        "ms-001:REQ_020": {
            "completed": False,
            "implementations": 0,
            "implementation_type": "N/A",
            "automated_tests": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "missing": 0,
                "not_applicable": True,
            },
            "manual_tests": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "missing": 1,
                "not_applicable": False,
            },
        },
    },
    "totals": {
        "requirements": {
            "total": 2,
            "completed": 1,
            "with_implementation": 1,
            "without_implementation": {"total": 1, "completed": 0},
        },
        "svcs": {"total": 4},
        "tests": {"total": 4, "passed": 4, "failed": 0, "skipped": 0, "missing_automated": 0, "missing_manual": 1},
        "automated_tests": {"total": 3, "passed": 3, "failed": 0},
        "manual_tests": {"total": 1, "passed": 1, "failed": 0},
    },
}


def test_status_minimal(status_schema):
    jsonschema.validate(MINIMAL_STATUS, status_schema)


def test_status_full(status_schema):
    jsonschema.validate(FULL_STATUS, status_schema)


# ── Status schema: negative cases ─────────────────────────────────────────────


def test_status_missing_metadata(status_schema):
    doc = {k: v for k, v in MINIMAL_STATUS.items() if k != "metadata"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, status_schema)


def test_status_missing_totals(status_schema):
    doc = {k: v for k, v in MINIMAL_STATUS.items() if k != "totals"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, status_schema)


def test_status_extra_top_level_field(status_schema):
    doc = {**MINIMAL_STATUS, "extra": True}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, status_schema)


def test_status_invalid_implementation_type(status_schema):
    doc = json.loads(json.dumps(FULL_STATUS))
    doc["requirements"]["ms-001:REQ_010"]["implementation_type"] = "invalid"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, status_schema)


def test_status_negative_test_count(status_schema):
    doc = json.loads(json.dumps(FULL_STATUS))
    doc["requirements"]["ms-001:REQ_010"]["automated_tests"]["total"] = -1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, status_schema)


# ── Export schema: positive cases ─────────────────────────────────────────────

MINIMAL_EXPORT = {
    "metadata": {
        "initial_urn": "ms-001",
        "urn_parsing_order": ["ms-001"],
        "import_graph": {},
        "filtered": False,
    },
    "requirements": {},
    "svcs": {},
    "mvrs": {},
    "annotations": {"implementations": {}, "tests": {}},
    "test_results": {},
}

FULL_EXPORT = {
    "metadata": {
        "initial_urn": "ms-001",
        "urn_parsing_order": ["sys-001", "ext-001", "ms-001"],
        "import_graph": {"sys-001": ["ext-001"], "ms-001": ["sys-001"]},
        "filtered": True,
    },
    "requirements": {
        "ms-001:REQ_010": {
            "urn": "ms-001",
            "id": "REQ_010",
            "title": "User authentication",
            "significance": "shall",
            "description": "The system shall authenticate users",
            "rationale": "Security requirement",
            "lifecycle": {"state": "effective", "reason": None},
            "implementation_type": "in-code",
            "categories": ["functional-suitability", "security"],
            "revision": {"major": 1, "minor": 0, "patch": 0},
            "references": [{"requirement_ids": ["sys-001:REQ_001"]}],
        }
    },
    "svcs": {
        "sys-001:SVC_010": {
            "urn": "sys-001",
            "id": "SVC_010",
            "title": "Verify authentication",
            "description": "Verify user auth works",
            "verification": "automated-test",
            "instructions": None,
            "lifecycle": {"state": "effective", "reason": None},
            "revision": {"major": 1, "minor": 0, "patch": 0},
            "requirement_ids": ["ms-001:REQ_010"],
        }
    },
    "mvrs": {
        "ms-001:MVR_201": {
            "urn": "ms-001",
            "id": "MVR_201",
            "passed": True,
            "comment": None,
            "svc_ids": ["sys-001:SVC_021"],
        }
    },
    "annotations": {
        "implementations": {
            "ms-001:REQ_010": [{"element_kind": "METHOD", "fully_qualified_name": "com.example.Foo.bar"}]
        },
        "tests": {
            "sys-001:SVC_010": [{"element_kind": "METHOD", "fully_qualified_name": "com.example.FooTest.testBar"}]
        },
    },
    "test_results": {
        "ms-001:com.example.FooTest.testBar": [
            {"fully_qualified_name": "com.example.FooTest.testBar", "status": "passed"}
        ]
    },
}


def test_export_minimal(export_schema):
    jsonschema.validate(MINIMAL_EXPORT, export_schema)


def test_export_full(export_schema):
    jsonschema.validate(FULL_EXPORT, export_schema)


def test_export_requirement_without_optional_fields(export_schema):
    doc = json.loads(json.dumps(MINIMAL_EXPORT))
    doc["requirements"]["ms-001:REQ_010"] = {
        "urn": "ms-001",
        "id": "REQ_010",
        "title": "Test",
        "significance": "shall",
        "description": "A test requirement",
        "lifecycle": {"state": "effective"},
        "implementation_type": "in-code",
        "categories": ["functional-suitability"],
        "revision": {"major": 1, "minor": 0, "patch": 0},
    }
    jsonschema.validate(doc, export_schema)


# ── Export schema: negative cases ─────────────────────────────────────────────


def test_export_missing_metadata(export_schema):
    doc = {k: v for k, v in MINIMAL_EXPORT.items() if k != "metadata"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_extra_top_level_field(export_schema):
    doc = {**MINIMAL_EXPORT, "extra": True}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_invalid_significance(export_schema):
    doc = json.loads(json.dumps(FULL_EXPORT))
    doc["requirements"]["ms-001:REQ_010"]["significance"] = "must"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_invalid_verification_type(export_schema):
    doc = json.loads(json.dumps(FULL_EXPORT))
    doc["svcs"]["sys-001:SVC_010"]["verification"] = "unknown"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_invalid_element_kind(export_schema):
    doc = json.loads(json.dumps(FULL_EXPORT))
    doc["annotations"]["implementations"]["ms-001:REQ_010"][0]["element_kind"] = "FUNCTION"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_invalid_test_status(export_schema):
    doc = json.loads(json.dumps(FULL_EXPORT))
    doc["test_results"]["ms-001:com.example.FooTest.testBar"][0]["status"] = "error"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_invalid_lifecycle_state(export_schema):
    doc = json.loads(json.dumps(FULL_EXPORT))
    doc["requirements"]["ms-001:REQ_010"]["lifecycle"]["state"] = "active"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)


def test_export_invalid_category(export_schema):
    doc = json.loads(json.dumps(FULL_EXPORT))
    doc["requirements"]["ms-001:REQ_010"]["categories"] = ["unknown-category"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, export_schema)
