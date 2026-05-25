# Copyright © reqstool

import pytest

from integration.reqstool.model_generators._regression_shared import (
    ECOSYSTEM_URNS,
    _GITHUB_TOKEN_ENV,
    _REGRESSION_REPO_BRANCH,
    _REGRESSION_REPO_URL,
)
from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.git_location import GitLocation
from reqstool.models.requirements import CATEGORIES, IMPLEMENTATION, SIGNIFICANCETYPES
from reqstool.models.svcs import VERIFICATIONTYPES
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository

# Ecosystems are implementation children — their requirement rows are excluded from the DB
# by DatabaseFilterProcessor after ingestion. Their SVCs and MVRs are retained.

# pytestmark is inherited from conftest.py (integration + skipif GITHUB_TOKEN).


@pytest.fixture(scope="module")
def repo():
    """Build the full SQLite DB from the regression monorepo and yield a repository for querying.

    The yield is inside the build_database context manager so the DB connection stays open
    for the duration of the module. Tests using this fixture must be read-only — any write
    attempt is blocked by RequirementsDatabase's authorizer callback.

    If fixture setup fails the assertion, pytest reports an ERROR (not FAILED) — this is
    intentional: it is a precondition failure, not a test assertion.
    """
    holder = ValidationErrorHolder()
    with build_database(
        location=GitLocation(
            env_token=_GITHUB_TOKEN_ENV,
            url=_REGRESSION_REPO_URL,
            branch=_REGRESSION_REPO_BRANCH,
            path="fixtures/parent",
        ),
        semantic_validator=SemanticValidator(validation_error_holder=holder),
    ) as (db, _):
        assert holder.get_no_of_errors() == 0, f"Unexpected validation errors: {holder.get_errors()}"
        repo_ = RequirementsRepository(db)
        assert (
            repo_.get_initial_urn() == "reqstool-regression"
        ), f"Wrong entry point: got {repo_.get_initial_urn()!r}, expected 'reqstool-regression'"
        yield repo_


# ---------------------------------------------------------------------------
# URN: reqstool-regression (parent layer)
# 4 reqs, 7 SVCs, 2 MVRs — see fixtures/parent/requirements.yml and svcs.yml
# ---------------------------------------------------------------------------


def test_parent_requirement_counts(repo):
    assert len(repo.get_all_requirements(urn="reqstool-regression")) == 4  # REQ_001–REQ_004


def test_parent_req_001(repo):
    req = repo.get_all_requirements(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="REQ_001")]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.RELIABILITY in req.categories


def test_parent_req_002(repo):
    req = repo.get_all_requirements(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="REQ_002")]
    assert req.significance == SIGNIFICANCETYPES.MAY
    assert req.lifecycle.state == LIFECYCLESTATE.DRAFT
    assert CATEGORIES.SECURITY in req.categories
    assert req.implementation == IMPLEMENTATION.NOT_APPLICABLE


def test_parent_req_003(repo):
    req = repo.get_all_requirements(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="REQ_003")]
    assert req.significance == SIGNIFICANCETYPES.SHOULD
    assert req.lifecycle.state == LIFECYCLESTATE.DEPRECATED
    assert CATEGORIES.MAINTAINABILITY in req.categories


def test_parent_req_004(repo):
    req = repo.get_all_requirements(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="REQ_004")]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.OBSOLETE
    assert CATEGORIES.FLEXIBILITY in req.categories


def test_parent_svc_counts(repo):
    assert len(repo.get_all_svcs(urn="reqstool-regression")) == 7  # SVC_001–SVC_007


def test_parent_svc_001(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_001")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="reqstool-regression", id="REQ_001") in svc.requirement_ids


def test_parent_svc_002(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_002")]
    assert svc.verification == VERIFICATIONTYPES.MANUAL_TEST
    assert UrnId(urn="reqstool-regression", id="REQ_001") in svc.requirement_ids
    assert UrnId(urn="regression-base-a", id="REQ_A01") in svc.requirement_ids


def test_parent_svc_003(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_003")]
    assert svc.verification == VERIFICATIONTYPES.REVIEW
    assert UrnId(urn="reqstool-regression", id="REQ_002") in svc.requirement_ids


def test_parent_svc_004(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_004")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.DEPRECATED
    assert UrnId(urn="reqstool-regression", id="REQ_003") in svc.requirement_ids


def test_parent_svc_005(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_005")]
    assert svc.verification == VERIFICATIONTYPES.PLATFORM
    assert svc.lifecycle.state == LIFECYCLESTATE.OBSOLETE
    assert UrnId(urn="reqstool-regression", id="REQ_004") in svc.requirement_ids


def test_parent_svc_006(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_006")]
    assert svc.verification == VERIFICATIONTYPES.OTHER
    assert UrnId(urn="regression-base-a", id="REQ_A02") in svc.requirement_ids


def test_parent_svc_007(repo):
    svc = repo.get_all_svcs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="SVC_007")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert UrnId(urn="regression-base-b", id="REQ_B01") in svc.requirement_ids


def test_parent_mvr_counts(repo):
    assert len(repo.get_all_mvrs(urn="reqstool-regression")) == 2  # MVR_001–MVR_002


def test_parent_mvr_001(repo):
    mvr = repo.get_all_mvrs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="MVR_001")]
    assert mvr.passed is True
    assert UrnId(urn="reqstool-regression", id="SVC_002") in mvr.svc_ids


def test_parent_mvr_002(repo):
    mvr = repo.get_all_mvrs(urn="reqstool-regression")[UrnId(urn="reqstool-regression", id="MVR_002")]
    assert mvr.passed is True
    assert UrnId(urn="reqstool-regression", id="SVC_003") in mvr.svc_ids


# ---------------------------------------------------------------------------
# URN: regression-base-a
# 2 reqs, 2 SVCs, 1 MVR — see fixtures/parent/base-a/
# ---------------------------------------------------------------------------


def test_base_a_requirement_counts(repo):
    assert len(repo.get_all_requirements(urn="regression-base-a")) == 2  # REQ_A01, REQ_A02


def test_base_a_req_a01(repo):
    req = repo.get_all_requirements(urn="regression-base-a")[UrnId(urn="regression-base-a", id="REQ_A01")]
    assert req.significance == SIGNIFICANCETYPES.SHALL
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.FUNCTIONAL_SUITABILITY in req.categories


def test_base_a_req_a02(repo):
    req = repo.get_all_requirements(urn="regression-base-a")[UrnId(urn="regression-base-a", id="REQ_A02")]
    assert req.significance == SIGNIFICANCETYPES.SHOULD
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.SAFETY in req.categories
    assert req.implementation == IMPLEMENTATION.NOT_APPLICABLE


def test_base_a_svc_counts(repo):
    assert len(repo.get_all_svcs(urn="regression-base-a")) == 2  # SVC_A01, SVC_A02


def test_base_a_svc_a01(repo):
    svc = repo.get_all_svcs(urn="regression-base-a")[UrnId(urn="regression-base-a", id="SVC_A01")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="regression-base-a", id="REQ_A01") in svc.requirement_ids


def test_base_a_svc_a02(repo):
    svc = repo.get_all_svcs(urn="regression-base-a")[UrnId(urn="regression-base-a", id="SVC_A02")]
    assert svc.verification == VERIFICATIONTYPES.MANUAL_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="regression-base-a", id="REQ_A02") in svc.requirement_ids


def test_base_a_mvr_counts(repo):
    assert len(repo.get_all_mvrs(urn="regression-base-a")) == 1  # MVR_A01


def test_base_a_mvr_a01(repo):
    mvr = repo.get_all_mvrs(urn="regression-base-a")[UrnId(urn="regression-base-a", id="MVR_A01")]
    assert mvr.passed is True
    assert UrnId(urn="regression-base-a", id="SVC_A02") in mvr.svc_ids


# ---------------------------------------------------------------------------
# URN: regression-base-b
# REQ_B02 is excluded by the filter defined in the parent's requirements.yml —
# only REQ_B01 survives. See fixtures/parent/requirements.yml filters section.
# ---------------------------------------------------------------------------


def test_base_b_in_db(repo):
    """Guard: regression-base-b must be present so subsequent base-b tests are not false positives."""
    assert repo.get_urn_info("regression-base-b") is not None


def test_base_b_requirement_counts(repo):
    assert len(repo.get_all_requirements(urn="regression-base-b")) == 1  # REQ_B02 excluded by filter


def test_base_b_req_b01(repo):
    req = repo.get_all_requirements(urn="regression-base-b")[UrnId(urn="regression-base-b", id="REQ_B01")]
    assert req.significance == SIGNIFICANCETYPES.MAY
    assert req.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert CATEGORIES.PERFORMANCE_EFFICIENCY in req.categories


def test_base_b_req_b02_filtered(repo):
    assert UrnId(urn="regression-base-b", id="REQ_B02") not in repo.get_all_requirements(urn="regression-base-b")


def test_base_b_svc_counts(repo):
    assert len(repo.get_all_svcs(urn="regression-base-b")) == 1  # SVC_B01


def test_base_b_svc_b01(repo):
    svc = repo.get_all_svcs(urn="regression-base-b")[UrnId(urn="regression-base-b", id="SVC_B01")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc.lifecycle.state == LIFECYCLESTATE.EFFECTIVE
    assert UrnId(urn="regression-base-b", id="REQ_B01") in svc.requirement_ids


def test_base_b_no_mvrs(repo):
    assert len(repo.get_all_mvrs(urn="regression-base-b")) == 0  # no MVRs in fixtures/parent/base-b/


# ---------------------------------------------------------------------------
# URN: regression-{python,java,typescript} — ecosystem layers
#
# Ecosystem requirement rows are excluded from the DB by DatabaseFilterProcessor
# (implementation-chain children). Their SVCs and MVRs are retained, but SVC
# requirement_id links pointing to filtered ecosystem reqs are cascade-deleted.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_requirements_excluded(repo, ecosystem_urn):
    assert len(repo.get_all_requirements(urn=ecosystem_urn)) == 0


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_svc_counts(repo, ecosystem_urn):
    assert len(repo.get_all_svcs(urn=ecosystem_urn)) == 3  # SVC_L01, SVC_L02, SVC_L03


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_svc_l01(repo, ecosystem_urn):
    svc = repo.get_all_svcs(urn=ecosystem_urn)[UrnId(urn=ecosystem_urn, id="SVC_L01")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    # REQ_L01 (ecosystem-own req) is cascade-deleted from svc_requirement_links when the
    # ecosystem requirement row is removed by DatabaseFilterProcessor; the cross-URN link survives.
    assert UrnId(urn=ecosystem_urn, id="REQ_L01") not in svc.requirement_ids
    assert UrnId(urn="reqstool-regression", id="REQ_001") in svc.requirement_ids


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_svc_l02(repo, ecosystem_urn):
    svcs = repo.get_all_svcs(urn=ecosystem_urn)
    assert UrnId(urn=ecosystem_urn, id="SVC_L02") in svcs, "SVC_L02 must exist even with empty requirement_ids"
    svc = svcs[UrnId(urn=ecosystem_urn, id="SVC_L02")]
    assert svc.verification == VERIFICATIONTYPES.MANUAL_TEST
    # REQ_L02 (ecosystem-own req) is cascade-deleted — SVC_L02 has no surviving requirement_ids
    assert len(svc.requirement_ids) == 0


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_svc_l03(repo, ecosystem_urn):
    svc = repo.get_all_svcs(urn=ecosystem_urn)[UrnId(urn=ecosystem_urn, id="SVC_L03")]
    assert svc.verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert UrnId(urn="regression-base-a", id="REQ_A01") in svc.requirement_ids


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_mvr_counts(repo, ecosystem_urn):
    assert len(repo.get_all_mvrs(urn=ecosystem_urn)) == 2  # MVR_L01, MVR_L02


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_mvr_l01(repo, ecosystem_urn):
    mvr = repo.get_all_mvrs(urn=ecosystem_urn)[UrnId(urn=ecosystem_urn, id="MVR_L01")]
    assert mvr.passed is True
    assert UrnId(urn=ecosystem_urn, id="SVC_L02") in mvr.svc_ids


@pytest.mark.parametrize("ecosystem_urn", ECOSYSTEM_URNS)
def test_ecosystem_mvr_l02(repo, ecosystem_urn):
    mvr = repo.get_all_mvrs(urn=ecosystem_urn)[UrnId(urn=ecosystem_urn, id="MVR_L02")]
    assert mvr.passed is True
    assert UrnId(urn="reqstool-regression", id="SVC_006") in mvr.svc_ids
