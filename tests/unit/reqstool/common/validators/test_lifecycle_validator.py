# Copyright © LFV

import pytest
from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository
from reqstool_python_decorators.decorators.decorators import SVCs


@pytest.fixture
def lifecycle_repo(local_testdata_resources_rootdir_w_path):
    db = RequirementsDatabase()
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/lifecycle/ms-101")),
        semantic_validator=semantic_validator,
        database=db,
    )
    repo = RequirementsRepository(db)
    yield repo
    db.close()


@SVCs("SVC_LIFECYCLE_0004")
def test_defunct_states(lifecycle_repo, caplog):

    LifecycleValidator(lifecycle_repo)

    assert "Urn ms-101:SVC_102 is used in an annotation despite being obsolete." in caplog.text
    assert (
        "The requirement ms-101:REQ_203 is marked as obsolete but the SVCs ms-101:SVC_202, ms-101:SVC_203 references it."
        in caplog.text
    )
    assert "Urn ms-101:REQ_101 is used in an annotation despite being deprecated." in caplog.text
    assert "Urn ms-101:SVC_101 is used in an annotation despite being deprecated." in caplog.text


@SVCs("SVC_LIFECYCLE_0004")
def test_active_states(lifecycle_repo, caplog):

    LifecycleValidator(lifecycle_repo)

    assert "The SVC ms-101:SVC_202 is marked as effective but the MVR ms-101:MVR_202 references it." not in caplog.text
    assert "Urn ms-101:REQ_201 is used in an annotation despite being draft." not in caplog.text
    assert "The SVC ms-101:SVC_201 is marked as draft but the MVR ms-101:MVR_201 references it." not in caplog.text


@SVCs("SVC_PARSE_0001")
def test_invalid_schema(local_testdata_resources_rootdir_w_path, caplog):
    with pytest.raises(SystemExit) as excinfo:
        semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
        CombinedRawDatasetsGenerator(
            initial_location=LocalLocation(
                path=local_testdata_resources_rootdir_w_path("test_basic/lifecycle/validation_error")
            ),
            semantic_validator=semantic_validator,
        ).combined_raw_datasets

    assert excinfo.type == SystemExit
    # 128 schema validation error
    assert str(excinfo.value) == "128"
    assert "'reason' is a required property" in caplog.text


@SVCs("SVC_LIFECYCLE_0002")
def test_requirement_lifecycle_state_parsed(lifecycle_repo):
    """LIFECYCLE_0002: a requirement's declared lifecycle state is recorded; absence defaults to effective."""
    reqs = lifecycle_repo.get_all_requirements()

    assert reqs[UrnId(urn="ms-101", id="REQ_101")].lifecycle.state is LIFECYCLESTATE.DEPRECATED
    assert reqs[UrnId(urn="ms-101", id="REQ_102")].lifecycle.state is LIFECYCLESTATE.OBSOLETE
    assert reqs[UrnId(urn="ms-101", id="REQ_201")].lifecycle.state is LIFECYCLESTATE.DRAFT
    # REQ_202 declares no lifecycle block → defaults to effective
    assert reqs[UrnId(urn="ms-101", id="REQ_202")].lifecycle.state is LIFECYCLESTATE.EFFECTIVE


@SVCs("SVC_LIFECYCLE_0003")
def test_svc_lifecycle_state_parsed(lifecycle_repo):
    """LIFECYCLE_0003: an SVC's declared lifecycle state is recorded; absence defaults to effective."""
    svcs = lifecycle_repo.get_all_svcs()

    assert svcs[UrnId(urn="ms-101", id="SVC_101")].lifecycle.state is LIFECYCLESTATE.DEPRECATED
    assert svcs[UrnId(urn="ms-101", id="SVC_102")].lifecycle.state is LIFECYCLESTATE.OBSOLETE
    assert svcs[UrnId(urn="ms-101", id="SVC_201")].lifecycle.state is LIFECYCLESTATE.DRAFT
    # SVC_202 declares no lifecycle block → defaults to effective
    assert svcs[UrnId(urn="ms-101", id="SVC_202")].lifecycle.state is LIFECYCLESTATE.EFFECTIVE
