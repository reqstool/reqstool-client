# Copyright © LFV

import os

import pytest

# Note: SVC_SOURCE_0004 (git) and SVC_SOURCE_0005 (maven) are exercised here, but are linked to the
# unit tests (test_git_location.py / test_maven_location.py) instead — this integration test is
# skipped without GITHUB/GITLAB tokens, so its result cannot satisfy those SVCs in credential-less CI.

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.locations.maven_location import MavenLocation
from reqstool.model_generators import combined_raw_datasets_generator


def choose_token():
    return os.getenv("GITHUB_TOKEN") or os.getenv("GITLAB_TOKEN")


@pytest.mark.integration
@pytest.mark.skipif(
    not (os.getenv("GITHUB_TOKEN") or os.getenv("GITLAB_TOKEN")),
    reason="Test needs GITHUB_TOKEN or GITLAB_TOKEN",
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


@pytest.mark.integration
@pytest.mark.skipif(
    not (os.getenv("GITHUB_TOKEN") or os.getenv("GITLAB_TOKEN")),
    reason="Test needs GITHUB_TOKEN or GITLAB_TOKEN",
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
