# Copyright © LFV

import logging

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationError, ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators import combined_raw_datasets_generator


@pytest.fixture
def get_validation(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    holder = ValidationErrorHolder()
    semantic_validator = SemanticValidator(validation_error_holder=holder)
    img = combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_errors/ms-101")),
        semantic_validator=semantic_validator,
    )

    return img.combined_raw_datasets


@pytest.fixture
def get_svcs_data_raw():
    # Data is raw since it's parsed directly from yaml data at runtime
    data = {
        "filters": {
            "sys-001": {"svc_ids": {"includes": ["SVC_sys001_101", "SVC_sys001_109"], "excludes": ["SVC_sys001_101"]}}
        },
        "cases": {},
    }
    return data


@pytest.fixture
def get_systems_data_raw():
    # Data is raw since it's parsed directly from yaml data at runtime
    data = {
        "path": "../sys-001",
        "filters": {"sys-001": {"requirement_ids": {"includes": ["REQ_sys001_101"], "excludes": ["REQ_sys001_102"]}}},
    }

    return data


@pytest.fixture
def get_requirements_data_raw():
    # Data is raw since it's parsed directly from yaml data at runtime
    data = {
        "metadata": {
            "urn": "ms-001",
            "variant": "microservice",
            "title": "Some Microservice Requirement Title",
            "url": "https://url.example.com",
        },
        "systems": {
            "local": [
                {
                    "path": "../sys-001",
                    "filters": {
                        "sys-001": {"requirement_ids": {"includes": ["REQ_sys001_103", "ext001:REQ_ext003_101"]}}
                    },
                }
            ]
        },
        "requirements": [
            {
                "id": "REQ_ms001_101",
                "title": "Title REQ_ms001_101",
                "significance": "may",
                "description": "Description REQ_ms001_101",
                "rationale": "Rationale REQ_ms001_101",
                "categories": ["maintainability", "functional-suitability"],
                "revision": "0.0.1",
            },
            {
                "id": "REQ_ms001_101",
                "title": "Title REQ_ms001_102",
                "significance": "may",
                "description": "Some description REQ_ms001_102",
                "rationale": "Rationale REQ_ms001_102",
                "categories": ["maintainability", "functional-suitability"],
                "references": {"requirement_ids": ["sys-001:REQ_sys001_101"]},
                "revision": "0.0.1",
            },
        ],
    }

    return data


@pytest.fixture
def get_svc_data():
    # Data is raw since it's parsed directly from yaml data at runtime
    data = {
        "filters": {"sys-001": {"svc_ids": {"includes": ["SVC_sys001_101", "SVC_sys001_109"]}}},
        "cases": [
            {
                "id": "SVC_ms001_101",
                "requirement_ids": ["REQ_ms001_101"],
                "title": "Some Title SVC_ms001_101",
                "verification": "automated-test",
                "revision": "0.0.1",
            },
            {
                "id": "SVC_ms001_101",
                "requirement_ids": ["REQ_ms001_102"],
                "title": "Some Title SVC_ms001_102",
                "verification": "manual-test",
                "revision": "0.0.1",
            },
            {
                "id": "SVC_ms001_103",
                "requirement_ids": ["sys-001:REQ_sys001_103"],
                "title": "Some Title SVC_ms001_103",
                "description": "Some Description SVC_ms001_103",
                "verification": "automated-test",
                "instructions": "Some instructions",
                "revision": "0.0.2",
            },
        ],
    }

    return data


def test_basic_validation(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    holder = ValidationErrorHolder()
    semantic_validator = SemanticValidator(validation_error_holder=holder)

    img = combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_errors/ms-101")),
        semantic_validator=semantic_validator,
    )

    assert img.combined_raw_datasets.raw_datasets

    errors = semantic_validator._validation_error_holder.get_errors()

    assert len(errors) == 7


@SVCs("SVC_016")
def test_validate_no_duplicate_reqs(get_requirements_data_raw):
    holder = ValidationErrorHolder()
    semantic_validator = SemanticValidator(validation_error_holder=holder)
    has_errors = semantic_validator._validate_no_duplicate_requirement_ids(get_requirements_data_raw)
    assert has_errors is True


@SVCs("SVC_017")
def test_validate_no_duplicate_svcs(get_svc_data):
    holder = ValidationErrorHolder()
    semantic_validator = SemanticValidator(validation_error_holder=holder)
    has_errors = semantic_validator._validate_no_duplicate_svc_ids(get_svc_data)
    assert has_errors is True


@SVCs("SVC_018")
def test_validate_svc_to_existing_reqs(get_validation):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    errors = semantic_validator._validate_svc_refers_to_existing_requirement_ids(get_validation)
    expected_error = """SVC '<ms-101:SVC_201>' refers to
                                    non-existing requirement id: <ms-101:REQ_20101>"""
    assert expected_error in errors[0].msg


@SVCs("SVC_018")
def test_validate_impls_to_existing_reqs(get_validation):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    errors = semantic_validator._validate_annotation_impls_refers_to_existing_requirement_ids(get_validation)
    expected_error = """Annotation refers to
                            non-existing requirement id: <ms-101:REQ_10101>"""
    assert expected_error in errors[0].msg


@SVCs("SVC_019")
def test_validate_tests_to_existing_svcs(get_validation):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    errors = semantic_validator._validate_annotation_tests_refers_to_existing_svc_ids(get_validation)
    expected_error_1 = "Annotation refers to non-existing svc id: <ms-101:SVC_101121>"
    expected_error_2 = "Annotation refers to non-existing svc id: <ms-101:SVC_102>"
    assert expected_error_1 in errors[0].msg
    assert expected_error_2 in errors[1].msg


@SVCs("SVC_019")
def test_validate_mvrs_to_existing_svcs(get_validation):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    errors = semantic_validator._validate_mvr_refers_to_existing_svc_ids(get_validation)
    expected_error = "MVR refers to non-existing svc id: <ms-101:SVC_20111>"
    assert expected_error in errors[0].msg


def test_validate_svc_filter_exlude_xor_import(get_svcs_data_raw):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    has_errors = semantic_validator._validate_svc_imports_filter_has_excludes_xor_includes(get_svcs_data_raw)
    expected_error = "Both imports and exclude filters applied to svc! (urn: sys-001)"
    errors = semantic_validator._validation_error_holder.get_errors()
    assert has_errors > 0
    assert expected_error in errors[0].msg


def test_validate_req_filter_exlude_xor_import(get_systems_data_raw):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    has_errors = semantic_validator._validate_req_imports_filter_has_excludes_xor_includes(get_systems_data_raw)
    expected_error = "Both imports and exclude filters applied to req! (urn: sys-001)"
    errors = semantic_validator._validation_error_holder.get_errors()
    assert has_errors > 0
    assert expected_error in errors[0].msg


# ---------------------------------------------------------------------------
# Happy-path tests (no errors)
# ---------------------------------------------------------------------------


def test_validate_no_duplicate_reqs_unique_ids_no_error():
    """Unique requirement IDs produce no error."""
    data = {
        "metadata": {"urn": "ms-001"},
        "requirements": [{"id": "REQ_A"}, {"id": "REQ_B"}],
    }
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_no_duplicate_requirement_ids(data)
    assert holder.get_no_of_errors() == 0


def test_validate_no_duplicate_reqs_systems_key_no_error():
    """Dict with 'systems' key but no 'requirements' does not trigger error."""
    data = {"metadata": {"urn": "ms-sys"}, "systems": {"local": []}}
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_no_duplicate_requirement_ids(data)
    assert holder.get_no_of_errors() == 0


def test_validate_no_duplicate_reqs_neither_key_adds_error():
    """Dict with neither 'requirements' nor 'systems' key adds an error."""
    data = {"metadata": {"urn": "ms-bad"}}
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_no_duplicate_requirement_ids(data)
    assert holder.get_no_of_errors() == 1
    assert "No requirements found" in holder.get_errors()[0].msg


def test_validate_no_duplicate_svcs_unique_ids_no_error():
    """Unique SVC IDs produce no error."""
    data = {
        "cases": [
            {"id": "SVC_001", "requirement_ids": []},
            {"id": "SVC_002", "requirement_ids": []},
        ]
    }
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_no_duplicate_svc_ids(data)
    assert holder.get_no_of_errors() == 0


def test_validate_no_duplicate_svcs_no_cases_adds_error():
    """Dict with no 'cases' key adds an error."""
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_no_duplicate_svc_ids({})
    assert holder.get_no_of_errors() == 1
    assert "No svc cases found" in holder.get_errors()[0].msg


def test_validate_svc_filter_only_includes_no_error():
    """SVC filter with only includes (no excludes) produces no error."""
    data = {
        "filters": {"sys-001": {"svc_ids": {"includes": ["SVC_001"]}}},
        "cases": {},
    }
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_svc_imports_filter_has_excludes_xor_includes(data)
    assert holder.get_no_of_errors() == 0


def test_validate_req_filter_only_excludes_no_error():
    """Req filter with only excludes (no includes) produces no error."""
    data = {
        "filters": {"sys-001": {"requirement_ids": {"excludes": ["REQ_001"]}}},
    }
    holder = ValidationErrorHolder()
    SemanticValidator(validation_error_holder=holder)._validate_req_imports_filter_has_excludes_xor_includes(data)
    assert holder.get_no_of_errors() == 0


# ---------------------------------------------------------------------------
# prettify_urn_id
# ---------------------------------------------------------------------------


def test_prettify_urn_id():
    """prettify_urn_id formats as <urn:id>."""
    sv = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    assert sv.prettify_urn_id(UrnId(urn="ms-001", id="REQ_001")) == "<ms-001:REQ_001>"


# ---------------------------------------------------------------------------
# _log_all_errors
# ---------------------------------------------------------------------------


def test_log_all_errors_pass_when_no_errors(caplog):
    """_log_all_errors logs VALIDATION: PASS when there are no errors."""
    holder = ValidationErrorHolder()
    sv = SemanticValidator(validation_error_holder=holder)
    with caplog.at_level(logging.INFO):
        sv._log_all_errors()
    assert "VALIDATION" in caplog.text


def test_log_all_errors_includes_error_message(caplog):
    """_log_all_errors includes the error message when errors are present."""
    holder = ValidationErrorHolder()
    holder.add_error(ValidationError(msg="something went wrong"))
    sv = SemanticValidator(validation_error_holder=holder)
    with caplog.at_level(logging.INFO):
        sv._log_all_errors()
    assert "something went wrong" in caplog.text
