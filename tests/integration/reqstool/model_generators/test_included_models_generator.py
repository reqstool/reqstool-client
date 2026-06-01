# Copyright © LFV

import os

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.locations.maven_location import MavenLocation
from reqstool.model_generators import combined_raw_datasets_generator


def choose_token():
    return os.getenv("GITHUB_TOKEN") or os.getenv("GITLAB_TOKEN")


@SVCs("SVC_002")
@pytest.mark.integration
@pytest.mark.skipif(
    not (os.getenv("GITHUB_TOKEN")),
    reason="Test needs GITHUB_TOKEN",
)
def test_basic_git():
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())

    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=GitLocation(
            token=choose_token(),
            url="https://github.com/reqstool/reqstool-client.git",
            path="tests/resources/test_data/data/remote/test_standard/test_standard_maven_git/ms-001",
            ref="main",
        ),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_003", "SVC_008")
@pytest.mark.integration
@pytest.mark.skipif(
    not (os.getenv("GITHUB_TOKEN")),
    reason="Test needs GITHUB_TOKEN",
)
def test_basic_maven():
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())

    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        # Setup
        initial_location=MavenLocation(
            token=choose_token(),
            url="https://maven.pkg.github.com/reqstool/reqstool-demo",
            group_id="se.lfv.reqstool",
            artifact_id="reqstool-demo",
            version="0.0.4",
            classifier="reqstool",
        ),
        semantic_validator=semantic_validator,
    )
