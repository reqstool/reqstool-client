# Copyright © LFV

import pytest

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.model_generators.svcs_model_generator import SVCsModelGenerator
from reqstool.models.svcs import VERIFICATIONTYPES

SVCS_YML_FILE = "software_verification_cases.yml"
URN = "ms-001"


@pytest.fixture
def svcs_model_generator(resource_funcname_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    return SVCsModelGenerator(
        uri=resource_funcname_rootdir_w_path(SVCS_YML_FILE), semantic_validator=semantic_validator, urn=URN
    )


def test_svcs_model_generator(svcs_model_generator, resource_funcname_rootdir_w_path):
    assert svcs_model_generator.uri == resource_funcname_rootdir_w_path(SVCS_YML_FILE)

    model = svcs_model_generator.model

    assert len(model.cases) == 2

    assert model.cases[UrnId(urn="ms-001", id="SVC_001")].id.id == "SVC_001"
    assert model.cases[UrnId(urn="ms-001", id="SVC_001")].requirement_ids == [
        UrnId(urn="ms-001", id="REQ_001"),
        UrnId(urn="ms-001", id="REQ_002"),
    ]
    assert model.cases[UrnId(urn="ms-001", id="SVC_001")].title == "Some Title SVC_001"
    assert model.cases[UrnId(urn="ms-001", id="SVC_001")].verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert model.cases[UrnId(urn="ms-001", id="SVC_001")].revision.base_version == "0.0.1"

    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].id.id == "SVC_002"
    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].requirement_ids == [
        UrnId(urn="ms-001", id="REQ_001"),
        UrnId(urn="ms-001", id="REQ_002"),
    ]
    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].title == "Some Title SVC_002"
    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].description == "Some Description SVC_002"
    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].verification == VERIFICATIONTYPES.MANUAL_TEST
    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].instructions == "Some instructions"
    assert model.cases[UrnId(urn="ms-001", id="SVC_002")].revision.base_version == "0.0.2"


def test_lifecycle_variable_model_generator(svcs_model_generator):
    cases = svcs_model_generator.model.cases

    assert cases[UrnId(urn="ms-001", id="SVC_001")].lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert cases[UrnId(urn="ms-001", id="SVC_001")].lifecycle.reason is None
    assert cases[UrnId(urn="ms-001", id="SVC_002")].lifecycle.state == LIFECYCLESTATE.DRAFT
    assert cases[UrnId(urn="ms-001", id="SVC_002")].lifecycle.reason is None
    assert cases[UrnId(urn="ms-001", id="SVC_003")].lifecycle.state == LIFECYCLESTATE.OBSOLETE
    assert cases[UrnId(urn="ms-001", id="SVC_003")].lifecycle.reason == "Reason for being obsolete"
    assert cases[UrnId(urn="ms-001", id="SVC_004")].lifecycle.state == LIFECYCLESTATE.DRAFT
    assert cases[UrnId(urn="ms-001", id="SVC_004")].lifecycle.reason == "Unnecessary reason"
