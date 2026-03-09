# Copyright © LFV


from reqstool.common.dataclasses.lifecycle import LIFECYCLESTATE
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.model_generators.requirements_model_generator import RequirementsModelGenerator
from reqstool.models.requirements import CATEGORIES, SIGNIFICANCETYPES, VARIANTS

REQUIREMENTS_YML_FILE = "requirements.yml"

SYSTEM_REQUIREMENTS_MODEL_YML_FILE = REQUIREMENTS_YML_FILE
MICROSERVICE_REQUIREMENTS_MODEL_YML_FILE = REQUIREMENTS_YML_FILE
EXTERNAL_REQUIREMENTS_MODEL_YML_FILE = REQUIREMENTS_YML_FILE


def test_system_requirements_model_generator(resource_funcname_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    rmg = RequirementsModelGenerator(
        parent=None,
        filename=resource_funcname_rootdir_w_path(SYSTEM_REQUIREMENTS_MODEL_YML_FILE),
        semantic_validator=semantic_validator,
    )

    assert rmg.filename == resource_funcname_rootdir_w_path(SYSTEM_REQUIREMENTS_MODEL_YML_FILE)
    assert rmg.prefix_with_urn is False

    model = rmg.requirements_data

    # GENERAL
    assert model.metadata.urn == "sys-001"
    assert model.metadata.variant == VARIANTS.SYSTEM
    assert model.metadata.title == "Some System Requirement Title"
    assert model.metadata.url is None

    # IMPORTS
    assert len(model.imports) == 6

    # local
    assert model.imports[0].current_unresolved.path == "/some/local-sys-path"

    # git
    assert model.imports[1].current_unresolved.env_token == "GITLAB_TOKEN"
    assert model.imports[1].current_unresolved.url == "https://gitlab.sys-example.com"
    assert model.imports[1].current_unresolved.branch == "feature/sys"
    assert model.imports[1].current_unresolved.path == "/some/path"

    # maven #1
    assert model.imports[2].current_unresolved.env_token == "MAVEN_TOKEN"
    assert model.imports[2].current_unresolved.url == "https://repo.maven.org"
    assert model.imports[2].current_unresolved.group_id == "com.example.one"
    assert model.imports[2].current_unresolved.artifact_id == "test-one"
    assert model.imports[2].current_unresolved.version == "1.0.0"
    assert model.imports[2].current_unresolved.classifier == "someclassifier"

    # maven #2
    assert model.imports[3].current_unresolved.env_token is None
    assert model.imports[3].current_unresolved.url == "https://repo.maven.apache.org/maven2/"
    assert model.imports[3].current_unresolved.group_id == "com.example.two"
    assert model.imports[3].current_unresolved.artifact_id == "test-two"
    assert model.imports[3].current_unresolved.version == "0.0.2"
    assert model.imports[3].current_unresolved.classifier == "reqstool"

    # pypi #1
    assert model.imports[4].current_unresolved.env_token == "PYPI_TOKEN"
    assert model.imports[4].current_unresolved.url == "https://example.com/simple/"
    assert model.imports[4].current_unresolved.package == "package1"
    assert model.imports[4].current_unresolved.version == "1.0.0"

    # pypi #2
    assert model.imports[5].current_unresolved.env_token is None
    assert model.imports[5].current_unresolved.url == "https://pypi.org/simple/"
    assert model.imports[5].current_unresolved.package == "package2"
    assert model.imports[5].current_unresolved.version == "2.0.0"

    # IMPLEMENTATIONS
    assert len(model.implementations) == 4

    # local
    assert model.implementations[0].current_unresolved.path == "/some/local-impl-path"

    # git
    assert model.implementations[1].current_unresolved.env_token == "GITLAB_TOKEN"
    assert model.implementations[1].current_unresolved.url == "https://gitlab.impl-example.com"
    assert model.implementations[1].current_unresolved.branch == "feature/impl"
    assert model.implementations[1].current_unresolved.path == "README.md"

    # maven #1
    assert model.implementations[2].current_unresolved.url == "https://repo.maven.org"
    assert model.implementations[2].current_unresolved.group_id == "com.example.one"
    assert model.implementations[2].current_unresolved.artifact_id == "test-one"
    assert model.implementations[2].current_unresolved.version == "0.0.1"
    assert model.implementations[2].current_unresolved.classifier == "classifier1"

    # maven #2
    assert model.implementations[3].current_unresolved.url == "https://repo2.maven.org"
    assert model.implementations[3].current_unresolved.group_id == "com.example.two"
    assert model.implementations[3].current_unresolved.artifact_id == "test-two"
    assert model.implementations[3].current_unresolved.version == "0.0.2"
    assert model.implementations[3].current_unresolved.classifier == "classifier2"

    # REQUIREMENTS
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].id.id == "REQ_001"
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].title == "Title REQ_001"
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].significance == SIGNIFICANCETYPES.MAY
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].description == "Description REQ_001"
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].rationale == "Rationale REQ_001"
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].categories == [
        CATEGORIES.MAINTAINABILITY,
        CATEGORIES.FUNCTIONAL_SUITABILITY,
    ]

    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].references[0].requirement_ids == {
        UrnId(urn="sys-001", id="REQ_200")
    }
    assert model.requirements[UrnId(urn="sys-001", id="REQ_001")].revision.base_version == "0.0.1"


def test_microservice_requirements_model_generator(resource_funcname_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    rmg = RequirementsModelGenerator(
        parent=None,
        filename=resource_funcname_rootdir_w_path(MICROSERVICE_REQUIREMENTS_MODEL_YML_FILE),
        semantic_validator=semantic_validator,
    )

    assert rmg.filename == resource_funcname_rootdir_w_path(MICROSERVICE_REQUIREMENTS_MODEL_YML_FILE)
    assert rmg.prefix_with_urn is False

    model = rmg.requirements_data

    # GENERAL
    assert model.metadata.urn == "ms-001"
    assert model.metadata.variant == VARIANTS.MICROSERVICE
    assert model.metadata.title == "Some Microservice Requirement Title"
    assert model.metadata.url == "https://url.example.com"

    # IMPORTS
    assert len(model.imports) == 3

    # local
    assert model.imports[0].current_unresolved.path == "/some/local-ms-path"

    # git
    assert model.imports[1].current_unresolved.env_token == "GITLAB_TOKEN"
    assert model.imports[1].current_unresolved.url == "https://gitlab.ms-example.com"
    assert model.imports[1].current_unresolved.branch == "main"
    assert model.imports[1].current_unresolved.path == "/some/ms-path"

    # maven
    assert model.imports[2].current_unresolved.url == "https://repo.maven.org"
    assert model.imports[2].current_unresolved.group_id == "com.example.one"
    assert model.imports[2].current_unresolved.artifact_id == "test-one"
    assert model.imports[2].current_unresolved.version == "1.0.0"
    assert model.imports[2].current_unresolved.classifier == "someclassifier"

    # REQUIREMENTS
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].id.id == "REQ_001"
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].title == "Title REQ_001"
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].significance == SIGNIFICANCETYPES.SHALL
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].description == "Description REQ_001"
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].rationale == "Rationale REQ_001"
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].categories == [CATEGORIES.FUNCTIONAL_SUITABILITY]

    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].references == []
    assert model.requirements[UrnId(urn="ms-001", id="REQ_001")].revision.base_version == "0.0.1"


def test_external_requirements_model_generator(resource_funcname_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    rmg = RequirementsModelGenerator(
        parent=None,
        filename=resource_funcname_rootdir_w_path(EXTERNAL_REQUIREMENTS_MODEL_YML_FILE),
        semantic_validator=semantic_validator,
    )

    assert rmg.filename == resource_funcname_rootdir_w_path(EXTERNAL_REQUIREMENTS_MODEL_YML_FILE)
    assert rmg.prefix_with_urn is False

    model = rmg.requirements_data

    # GENERAL
    assert model.metadata.urn == "ext-001"
    assert model.metadata.variant == VARIANTS.EXTERNAL
    assert model.metadata.title == "Some System Requirement Title"
    assert model.metadata.url == "https://url.example.com"

    # REQUIREMENTS
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].id.id == "REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].title == "Title REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].significance == SIGNIFICANCETYPES.MAY
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].description == "Description REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].rationale == "Rationale REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].categories == [
        CATEGORIES.MAINTAINABILITY,
        CATEGORIES.FUNCTIONAL_SUITABILITY,
    ]

    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].references[0].requirement_ids == {
        UrnId(urn="ext-001", id="REQ_200")
    }
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].revision.base_version == "0.0.1"


def test_rational_optional_model_generator(resource_funcname_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    rmg = RequirementsModelGenerator(
        parent=None,
        filename=resource_funcname_rootdir_w_path(EXTERNAL_REQUIREMENTS_MODEL_YML_FILE),
        semantic_validator=semantic_validator,
    )

    assert rmg.filename == resource_funcname_rootdir_w_path(EXTERNAL_REQUIREMENTS_MODEL_YML_FILE)
    assert rmg.prefix_with_urn is False

    model = rmg.requirements_data

    # GENERAL
    assert model.metadata.urn == "ext-001"
    assert model.metadata.variant == VARIANTS.EXTERNAL
    assert model.metadata.title == "Some System Requirement Title"
    assert model.metadata.url == "https://url.example.com"

    # REQUIREMENTS
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].id.id == "REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].title == "Title REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].significance == SIGNIFICANCETYPES.MAY
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].description == "Description REQ_001"
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].rationale is None
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].categories == [
        CATEGORIES.MAINTAINABILITY,
        CATEGORIES.FUNCTIONAL_SUITABILITY,
    ]

    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].references[0].requirement_ids == {
        UrnId(urn="ext-001", id="REQ_200")
    }
    assert model.requirements[UrnId(urn="ext-001", id="REQ_001")].revision.base_version == "0.0.1"


def test_lifecycle_variable_model_generator(resource_funcname_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    rmg = RequirementsModelGenerator(
        parent=None,
        filename=resource_funcname_rootdir_w_path(EXTERNAL_REQUIREMENTS_MODEL_YML_FILE),
        semantic_validator=semantic_validator,
    )
    requirements = rmg.requirements_data.requirements

    assert requirements[UrnId(urn="ms-001", id="REQ_001")].lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert requirements[UrnId(urn="ms-001", id="REQ_001")].lifecycle.reason is None
    assert requirements[UrnId(urn="ms-001", id="REQ_002")].lifecycle.state == LIFECYCLESTATE.DRAFT
    assert requirements[UrnId(urn="ms-001", id="REQ_002")].lifecycle.reason is None
    assert requirements[UrnId(urn="ms-001", id="REQ_003")].lifecycle.state == LIFECYCLESTATE.OBSOLETE
    assert requirements[UrnId(urn="ms-001", id="REQ_003")].lifecycle.reason == "Reason for being obsolete"
    assert requirements[UrnId(urn="ms-001", id="REQ_004")].lifecycle.state == LIFECYCLESTATE.DRAFT
    assert requirements[UrnId(urn="ms-001", id="REQ_004")].lifecycle.reason == "Unnecessary reason"
