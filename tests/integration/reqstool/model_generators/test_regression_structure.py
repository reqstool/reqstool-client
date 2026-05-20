# Copyright © reqstool

import os
from typing import Dict

import pytest

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.model_generators import combined_raw_datasets_generator
from reqstool.models.raw_datasets import RawDataset
from reqstool.models.requirements import CATEGORIES, IMPLEMENTATION, SIGNIFICANCETYPES
from reqstool.models.svcs import VERIFICATIONTYPES

REGRESSION_REPO_URL = "https://github.com/reqstool/reqstool-regression.git"
REGRESSION_REPO_BRANCH = "main"
_GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

_ECOSYSTEM_URNS = ["regression-python", "regression-java", "regression-typescript"]

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv(_GITHUB_TOKEN_ENV, "").strip(),
        reason=f"Test needs {_GITHUB_TOKEN_ENV}",
    ),
]


@pytest.fixture(scope="module")
def combined() -> Dict[str, RawDataset]:
    """Clone the regression monorepo once (parent entry point) and return the raw_datasets dict."""
    holder = ValidationErrorHolder()
    gen = combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=GitLocation(
            env_token=_GITHUB_TOKEN_ENV,
            url=REGRESSION_REPO_URL,
            branch=REGRESSION_REPO_BRANCH,
            path="fixtures/parent",
        ),
        semantic_validator=SemanticValidator(validation_error_holder=holder),
    )
    assert holder.get_no_of_errors() == 0, f"Unexpected validation errors: {holder.get_errors()}"
    return gen.combined_raw_datasets.raw_datasets


# ---------------------------------------------------------------------------
# URN: reqstool-regression (parent layer)
# ---------------------------------------------------------------------------


def test_parent_requirement_counts(combined):
    assert len(combined["reqstool-regression"].requirements_data.requirements) == 4


def test_parent_req_001(combined):
    req = combined["reqstool-regression"].requirements_data.requirements[
        UrnId(urn="reqstool-regression", id="REQ_001")
    ]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.RELIABILITY in req.categories


def test_parent_req_002(combined):
    req = combined["reqstool-regression"].requirements_data.requirements[
        UrnId(urn="reqstool-regression", id="REQ_002")
    ]
    assert req.significance == SIGNIFICANCETYPES.MAY
    assert req.lifecycle.state == LIFECYCLESTATE.DRAFT
    assert CATEGORIES.SECURITY in req.categories
    assert req.implementation == IMPLEMENTATION.NOT_APPLICABLE


def test_parent_req_003(combined):
    req = combined["reqstool-regression"].requirements_data.requirements[
        UrnId(urn="reqstool-regression", id="REQ_003")
    ]
    assert req.significance == SIGNIFICANCETYPES.SHOULD
    assert req.lifecycle.state == LIFECYCLESTATE.DEPRECATED
    assert CATEGORIES.MAINTAINABILITY in req.categories


def test_parent_req_004(combined):
    req = combined["reqstool-regression"].requirements_data.requirements[
        UrnId(urn="reqstool-regression", id="REQ_004")
    ]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.OBSOLETE
    assert CATEGORIES.FLEXIBILITY in req.categories


def test_parent_svc_counts(combined):
    assert len(combined["reqstool-regression"].svcs_data.cases) == 7


def test_parent_svc_001(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_001")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="reqstool-regression", id="REQ_001") in svc.requirement_ids


def test_parent_svc_002(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_002")]
    assert svc.verification == VERIFICATIONTYPES.MANUAL_TEST
    assert UrnId(urn="reqstool-regression", id="REQ_001") in svc.requirement_ids
    assert UrnId(urn="regression-base-a", id="REQ_A01") in svc.requirement_ids


def test_parent_svc_003(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_003")]
    assert svc.verification == VERIFICATIONTYPES.REVIEW
    assert UrnId(urn="reqstool-regression", id="REQ_002") in svc.requirement_ids


def test_parent_svc_004(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_004")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.DEPRECATED
    assert UrnId(urn="reqstool-regression", id="REQ_003") in svc.requirement_ids


def test_parent_svc_005(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_005")]
    assert svc.verification == VERIFICATIONTYPES.PLATFORM
    assert svc.lifecycle.state == LIFECYCLESTATE.OBSOLETE
    assert UrnId(urn="reqstool-regression", id="REQ_004") in svc.requirement_ids


def test_parent_svc_006(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_006")]
    assert svc.verification == VERIFICATIONTYPES.OTHER
    assert UrnId(urn="regression-base-a", id="REQ_A02") in svc.requirement_ids


def test_parent_svc_007(combined):
    svc = combined["reqstool-regression"].svcs_data.cases[UrnId(urn="reqstool-regression", id="SVC_007")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert UrnId(urn="regression-base-b", id="REQ_B01") in svc.requirement_ids


def test_parent_mvr_counts(combined):
    assert len(combined["reqstool-regression"].mvrs_data.results) == 2


def test_parent_mvr_001(combined):
    mvr = combined["reqstool-regression"].mvrs_data.results[UrnId(urn="reqstool-regression", id="MVR_001")]
    assert mvr.passed is True
    assert UrnId(urn="reqstool-regression", id="SVC_002") in mvr.svc_ids


def test_parent_mvr_002(combined):
    mvr = combined["reqstool-regression"].mvrs_data.results[UrnId(urn="reqstool-regression", id="MVR_002")]
    assert mvr.passed is True
    assert UrnId(urn="reqstool-regression", id="SVC_003") in mvr.svc_ids


# ---------------------------------------------------------------------------
# URN: regression-base-a
# ---------------------------------------------------------------------------


def test_base_a_requirement_counts(combined):
    assert len(combined["regression-base-a"].requirements_data.requirements) == 2


def test_base_a_req_a01(combined):
    req = combined["regression-base-a"].requirements_data.requirements[
        UrnId(urn="regression-base-a", id="REQ_A01")
    ]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.FUNCTIONAL_SUITABILITY in req.categories


def test_base_a_req_a02(combined):
    req = combined["regression-base-a"].requirements_data.requirements[
        UrnId(urn="regression-base-a", id="REQ_A02")
    ]
    assert req.significance == SIGNIFICANCETYPES.SHOULD
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.SAFETY in req.categories
    assert req.implementation == IMPLEMENTATION.NOT_APPLICABLE


def test_base_a_svc_counts(combined):
    assert len(combined["regression-base-a"].svcs_data.cases) == 2


def test_base_a_svc_a01(combined):
    svc = combined["regression-base-a"].svcs_data.cases[UrnId(urn="regression-base-a", id="SVC_A01")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="regression-base-a", id="REQ_A01") in svc.requirement_ids


def test_base_a_svc_a02(combined):
    svc = combined["regression-base-a"].svcs_data.cases[UrnId(urn="regression-base-a", id="SVC_A02")]
    assert svc.verification == VERIFICATIONTYPES.MANUAL_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="regression-base-a", id="REQ_A02") in svc.requirement_ids


def test_base_a_mvr_counts(combined):
    assert len(combined["regression-base-a"].mvrs_data.results) == 1


def test_base_a_mvr_a01(combined):
    mvr = combined["regression-base-a"].mvrs_data.results[UrnId(urn="regression-base-a", id="MVR_A01")]
    assert mvr.passed is True
    assert UrnId(urn="regression-base-a", id="SVC_A02") in mvr.svc_ids


# ---------------------------------------------------------------------------
# URN: regression-base-b
# ---------------------------------------------------------------------------


def test_base_b_requirement_counts(combined):
    assert len(combined["regression-base-b"].requirements_data.requirements) == 2


def test_base_b_req_b01(combined):
    req = combined["regression-base-b"].requirements_data.requirements[
        UrnId(urn="regression-base-b", id="REQ_B01")
    ]
    assert req.significance == SIGNIFICANCETYPES.MAY
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.PERFORMANCE_EFFICIENCY in req.categories


def test_base_b_req_b02(combined):
    req = combined["regression-base-b"].requirements_data.requirements[
        UrnId(urn="regression-base-b", id="REQ_B02")
    ]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.COMPATIBILITY in req.categories


def test_base_b_svc_counts(combined):
    assert len(combined["regression-base-b"].svcs_data.cases) == 1


def test_base_b_svc_b01(combined):
    svc = combined["regression-base-b"].svcs_data.cases[UrnId(urn="regression-base-b", id="SVC_B01")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="regression-base-b", id="REQ_B01") in svc.requirement_ids


def test_base_b_no_mvrs(combined):
    rd = combined["regression-base-b"]
    assert rd.mvrs_data is None or len(rd.mvrs_data.results) == 0


# ---------------------------------------------------------------------------
# URN: regression-{python,java,typescript} — all three share the same structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_requirement_counts(combined, ecosystem_urn):
    assert len(combined[ecosystem_urn].requirements_data.requirements) == 2


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_req_l01(combined, ecosystem_urn):
    req = combined[ecosystem_urn].requirements_data.requirements[UrnId(urn=ecosystem_urn, id="REQ_L01")]
    assert req.significance == SIGNIFICANCETYPES.SHOULD
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.INTERACTION_CAPABILITY in req.categories


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_req_l02(combined, ecosystem_urn):
    req = combined[ecosystem_urn].requirements_data.requirements[UrnId(urn=ecosystem_urn, id="REQ_L02")]
    assert req.significance == SIGNIFICANCETYPES.MAY
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.COMPATIBILITY in req.categories
    assert req.implementation == IMPLEMENTATION.NOT_APPLICABLE


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_svc_counts(combined, ecosystem_urn):
    assert len(combined[ecosystem_urn].svcs_data.cases) == 3


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_svc_l01(combined, ecosystem_urn):
    svc = combined[ecosystem_urn].svcs_data.cases[UrnId(urn=ecosystem_urn, id="SVC_L01")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert UrnId(urn=ecosystem_urn, id="REQ_L01") in svc.requirement_ids
    assert UrnId(urn="reqstool-regression", id="REQ_001") in svc.requirement_ids


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_svc_l02(combined, ecosystem_urn):
    svc = combined[ecosystem_urn].svcs_data.cases[UrnId(urn=ecosystem_urn, id="SVC_L02")]
    assert svc.verification == VERIFICATIONTYPES.MANUAL_TEST
    assert UrnId(urn=ecosystem_urn, id="REQ_L02") in svc.requirement_ids


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_svc_l03(combined, ecosystem_urn):
    svc = combined[ecosystem_urn].svcs_data.cases[UrnId(urn=ecosystem_urn, id="SVC_L03")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert UrnId(urn="regression-base-a", id="REQ_A01") in svc.requirement_ids


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_mvr_counts(combined, ecosystem_urn):
    assert len(combined[ecosystem_urn].mvrs_data.results) == 2


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_mvr_l01(combined, ecosystem_urn):
    mvr = combined[ecosystem_urn].mvrs_data.results[UrnId(urn=ecosystem_urn, id="MVR_L01")]
    assert mvr.passed is True
    assert UrnId(urn=ecosystem_urn, id="SVC_L02") in mvr.svc_ids


@pytest.mark.parametrize("ecosystem_urn", _ECOSYSTEM_URNS)
def test_ecosystem_mvr_l02(combined, ecosystem_urn):
    mvr = combined[ecosystem_urn].mvrs_data.results[UrnId(urn=ecosystem_urn, id="MVR_L02")]
    assert mvr.passed is True
    assert UrnId(urn="reqstool-regression", id="SVC_006") in mvr.svc_ids
