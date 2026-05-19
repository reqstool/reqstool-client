# Copyright © reqstool

import os

import pytest

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.model_generators import combined_raw_datasets_generator

REGRESSION_REPO_URL = "https://github.com/reqstool/reqstool-regression.git"
# Branch is intentionally 'main' (always latest regression data).
# For stronger CI stability, pin to a commit SHA when the regression repo cuts stable releases.
REGRESSION_REPO_BRANCH = "main"
_GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

ECOSYSTEMS = [
    "fixtures/ecosystems/python",
    "fixtures/ecosystems/java",
    "fixtures/ecosystems/typescript",
]

_COMMON_URNS = frozenset({"reqstool-regression", "regression-base-a", "regression-base-b"})

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.getenv(_GITHUB_TOKEN_ENV), reason=f"Test needs {_GITHUB_TOKEN_ENV}"),
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


@pytest.mark.parametrize("ecosystem_path", ECOSYSTEMS)
def test_ecosystem_git_location(ecosystem_path):
    """Each ecosystem wrapper resolves correctly via GitLocation."""
    gen = _make_generator(
        GitLocation(
            env_token=_GITHUB_TOKEN_ENV,
            url=REGRESSION_REPO_URL,
            branch=REGRESSION_REPO_BRANCH,
            path=ecosystem_path,
        )
    )

    urns = set(gen.combined_raw_datasets.raw_datasets.keys())

    # Ecosystem-specific wrapper URN present (exact key lookup)
    ecosystem_name = ecosystem_path.split("/")[-1]
    assert f"regression-{ecosystem_name}" in urns, f"Expected regression-{ecosystem_name} URN in {urns}"

    # Parent and grandparent layers resolved
    assert _COMMON_URNS.issubset(urns), f"Expected {_COMMON_URNS} in {urns}"

    # base-b was loaded (REQ_B01 present)
    # Note: REQ_B02 exclusion is applied by DatabaseFilterProcessor at db-build time,
    # not at the raw-dataset level — so it cannot be verified here.
    all_req_ids = {
        req.id
        for rd in gen.combined_raw_datasets.raw_datasets.values()
        if rd.requirements_data
        for req in (rd.requirements_data.requirements or [])
    }
    assert "REQ_B01" in all_req_ids, "REQ_B01 should be present from base-b (confirms base-b was loaded)"


# ---------------------------------------------------------------------------
# Parent-entry aggregation test — git location
# ---------------------------------------------------------------------------


def test_parent_entry_aggregates_all_ecosystems():
    """Running from the parent entry point walks all ecosystem implementations."""
    gen = _make_generator(
        GitLocation(
            env_token=_GITHUB_TOKEN_ENV,
            url=REGRESSION_REPO_URL,
            branch=REGRESSION_REPO_BRANCH,
            path="fixtures/parent",
        )
    )

    urns = set(gen.combined_raw_datasets.raw_datasets.keys())

    # All ecosystem URNs present — derived from ECOSYSTEMS to stay in sync automatically
    for name in (p.split("/")[-1] for p in ECOSYSTEMS):
        assert f"regression-{name}" in urns, f"regression-{name} missing from aggregated urns: {urns}"

    # Parent and grandparents present
    assert _COMMON_URNS.issubset(urns), f"Expected {_COMMON_URNS} in {urns}"
