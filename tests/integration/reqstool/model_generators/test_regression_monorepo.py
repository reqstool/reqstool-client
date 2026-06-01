# Copyright © reqstool

import os

import pytest

from integration.reqstool.model_generators._regression_shared import (
    ECOSYSTEM_PATHS,
    _GITHUB_TOKEN_ENV,
    _REGRESSION_REPO_REF,
    _REGRESSION_REPO_URL,
)
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.model_generators import combined_raw_datasets_generator

_COMMON_URNS = frozenset({"reqstool-regression", "regression-base-a", "regression-base-b"})

# pytestmark is inherited from conftest.py (integration + skipif GITHUB_TOKEN).


def _make_generator(path: str, tmpdir_manager=None):
    """Clone the regression repo at *path* and return the generator.

    Validation errors abort the test immediately — no caller needs to check separately.
    Pass *tmpdir_manager* (module-scoped fixture) so repeated calls with the same URL
    reuse the existing checkout rather than re-cloning.
    """
    holder = ValidationErrorHolder()
    gen = combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=GitLocation(
            token=os.getenv(_GITHUB_TOKEN_ENV),
            url=_REGRESSION_REPO_URL,
            ref=_REGRESSION_REPO_REF,
            path=path,
        ),
        semantic_validator=SemanticValidator(validation_error_holder=holder),
        tmpdir_manager=tmpdir_manager,
    )
    assert holder.get_no_of_errors() == 0, f"Unexpected validation errors: {holder.get_errors()}"
    return gen


def _all_req_ids(gen):
    """Collect all requirement IDs (bare id strings) across every URN in the combined dataset."""
    return {
        urn_id.id
        for rd in gen.combined_raw_datasets.raw_datasets.values()
        if rd.requirements_data
        for urn_id in rd.requirements_data.requirements  # iterates UrnId keys
    }


# ---------------------------------------------------------------------------
# Parameterized cross-ecosystem tests — git location axis
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ecosystem_path", ECOSYSTEM_PATHS)
def test_ecosystem_git_location(ecosystem_path, shared_tmpdir):
    """Each ecosystem wrapper resolves correctly via GitLocation."""
    gen = _make_generator(ecosystem_path, shared_tmpdir)

    urns = set(gen.combined_raw_datasets.raw_datasets.keys())

    # Ecosystem-specific wrapper URN present (exact key lookup)
    ecosystem_name = ecosystem_path.split("/")[-1]
    assert f"regression-{ecosystem_name}" in urns, f"Expected regression-{ecosystem_name} URN in {urns}"

    # Parent and grandparent layers resolved
    assert _COMMON_URNS.issubset(urns), f"Expected {_COMMON_URNS} in {urns}"

    # base-b data loaded — REQ_B01 present somewhere in the aggregated dataset.
    # Note: REQ_B02 exclusion is applied by DatabaseFilterProcessor at db-build time,
    # not at the raw-dataset level — see test_regression_structure::test_base_b_req_b02_filtered.
    assert "REQ_B01" in _all_req_ids(gen), "REQ_B01 should be present (confirms base-b data was loaded)"


# ---------------------------------------------------------------------------
# Parent-entry aggregation test — git location
# ---------------------------------------------------------------------------


def test_parent_entry_aggregates_all_ecosystems(shared_tmpdir):
    """Running from the parent entry point walks all ecosystem implementations."""
    gen = _make_generator("fixtures/parent", shared_tmpdir)

    urns = set(gen.combined_raw_datasets.raw_datasets.keys())

    # All ecosystem URNs present — derived from ECOSYSTEM_PATHS to stay in sync automatically
    for name in (p.split("/")[-1] for p in ECOSYSTEM_PATHS):
        assert f"regression-{name}" in urns, f"regression-{name} missing from aggregated urns: {urns}"

    # Parent and grandparents present
    assert _COMMON_URNS.issubset(urns), f"Expected {_COMMON_URNS} in {urns}"

    # Data was actually aggregated — REQ_B01 should be present from the base-b layer
    assert "REQ_B01" in _all_req_ids(gen), "REQ_B01 should be present (confirms base-b was aggregated)"
