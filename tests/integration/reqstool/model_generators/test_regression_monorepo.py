# Copyright © reqstool

import os

import pytest

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.model_generators import combined_raw_datasets_generator

REGRESSION_REPO_URL = "https://github.com/reqstool/reqstool-regression.git"
REGRESSION_REPO_BRANCH = "main"

ECOSYSTEMS = [
    "fixtures/ecosystems/python",
    "fixtures/ecosystems/java",
    "fixtures/ecosystems/typescript",
]


def _make_generator(initial_location):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    return combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=initial_location,
        semantic_validator=semantic_validator,
    )


# ---------------------------------------------------------------------------
# Parameterized cross-ecosystem tests — git location axis
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), reason="Test needs GITHUB_TOKEN")
@pytest.mark.parametrize("ecosystem_path", ECOSYSTEMS)
def test_ecosystem_git_location(ecosystem_path):
    """Each ecosystem wrapper resolves correctly via GitLocation."""
    gen = _make_generator(
        GitLocation(
            env_token="GITHUB_TOKEN",
            url=REGRESSION_REPO_URL,
            branch=REGRESSION_REPO_BRANCH,
            path=ecosystem_path,
        )
    )

    urns = set(gen.combined_raw_datasets.raw_datasets.keys())

    # Ecosystem-specific wrapper URN present
    ecosystem_name = ecosystem_path.split("/")[-1]
    assert any(f"regression-{ecosystem_name}" in u for u in urns), (
        f"Expected regression-{ecosystem_name} URN in {urns}"
    )

    # Parent layer resolved via local import
    assert "reqstool-regression" in urns, f"Parent URN missing from {urns}"

    # Grandparent layers resolved
    assert "regression-base-a" in urns, f"base-a URN missing from {urns}"
    assert "regression-base-b" in urns, f"base-b URN missing from {urns}"

    # REQ_B02 excluded by import filter
    from reqstool.models.requirements import UrnId

    req_b02 = UrnId(urn="regression-base-b", id="REQ_B02")
    all_req_ids = {
        req.id
        for rd in gen.combined_raw_datasets.raw_datasets.values()
        if rd.requirements_data
        for req in (rd.requirements_data.requirements or [])
    }
    assert req_b02 not in all_req_ids, "REQ_B02 should be filtered out"


# ---------------------------------------------------------------------------
# Parent-entry aggregation test — git location
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), reason="Test needs GITHUB_TOKEN")
def test_parent_entry_aggregates_all_ecosystems():
    """Running from the parent entry point walks all 3 ecosystem implementations."""
    gen = _make_generator(
        GitLocation(
            env_token="GITHUB_TOKEN",
            url=REGRESSION_REPO_URL,
            branch=REGRESSION_REPO_BRANCH,
            path="fixtures/parent",
        )
    )

    urns = set(gen.combined_raw_datasets.raw_datasets.keys())

    # All three ecosystem URNs present
    for name in ("python", "java", "typescript"):
        assert f"regression-{name}" in urns, f"regression-{name} missing from aggregated urns: {urns}"

    # Parent and grandparents present
    assert "reqstool-regression" in urns
    assert "regression-base-a" in urns
    assert "regression-base-b" in urns
