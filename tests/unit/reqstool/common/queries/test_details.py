# Copyright © LFV

import pytest

from reqstool.common.project_session import ProjectSession
from reqstool.common.models.urn_id import UrnId
from reqstool.common.queries.details import (
    get_mvr_details,
    get_requirement_details,
    get_requirement_status,
    get_requirements_status_all,
    get_svc_details,
)
from reqstool.models.annotations import AnnotationData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    RequirementData,
)
from reqstool.models.svcs import SVCData, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository
from reqstool.locations.local_location import LocalLocation


@pytest.fixture
def session(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    s = ProjectSession(LocalLocation(path=path))
    s.build()
    yield s
    s.close()


def test_get_requirement_details_known(session):
    result = get_requirement_details("REQ_010", session.repo)
    assert result is not None
    assert result["type"] == "requirement"
    assert result["id"] == "REQ_010"
    assert "title" in result
    assert "significance" in result
    assert "description" in result
    assert "lifecycle" in result
    assert isinstance(result["references"], list)
    assert isinstance(result["implementations"], list)
    assert isinstance(result["svcs"], list)
    assert "location" in result
    assert result["source_paths"] == {}  # no urn_source_paths passed


def test_get_requirement_details_with_source_paths(session):
    result = get_requirement_details("REQ_010", session.repo, session.urn_source_paths)
    assert result is not None
    assert isinstance(result["source_paths"], dict)


def test_get_requirement_details_unknown(session):
    assert get_requirement_details("REQ_NONEXISTENT", session.repo) is None


def test_get_requirement_details_implementations(session):
    result = get_requirement_details("REQ_010", session.repo, session.urn_source_paths)
    assert result is not None
    assert len(result["implementations"]) > 0
    impl = result["implementations"][0]
    assert "element_kind" in impl
    assert "fqn" in impl


def test_get_svc_details_known(session):
    repo = session.repo
    svc_ids = [uid.id for uid in repo.get_all_svcs()]
    assert svc_ids
    result = get_svc_details(svc_ids[0], repo)
    assert result is not None
    assert result["type"] == "svc"
    assert "title" in result
    assert "verification" in result
    assert "requirement_ids" in result
    assert "test_summary" in result
    assert set(result["test_summary"].keys()) == {"passed", "failed", "skipped", "missing"}
    assert "mvrs" in result


def test_get_svc_details_unknown(session):
    assert get_svc_details("SVC_NONEXISTENT", session.repo) is None


def test_get_svc_details_requirement_ids_enriched(session):
    repo = session.repo
    svc_ids = [uid.id for uid in repo.get_all_svcs()]
    for svc_id in svc_ids:
        result = get_svc_details(svc_id, repo)
        assert result is not None
        for req_entry in result["requirement_ids"]:
            assert "id" in req_entry
            assert "urn" in req_entry
            assert "title" in req_entry
            assert "lifecycle_state" in req_entry
        break


def test_get_mvr_details_unknown(session):
    assert get_mvr_details("MVR_NONEXISTENT", session.repo) is None


def test_get_requirement_status_known(session):
    result = get_requirement_status("REQ_010", session.repo)
    assert result is not None
    assert result["id"] == "REQ_010"
    assert "lifecycle_state" in result
    assert "implementation" in result
    assert "test_summary" in result
    assert set(result["test_summary"].keys()) == {"passed", "failed", "skipped", "missing"}
    assert "meets_requirements" in result
    assert isinstance(result["meets_requirements"], bool)


def test_get_requirement_status_unknown(session):
    assert get_requirement_status("REQ_NONEXISTENT", session.repo) is None


def _make_db_with_req(impl_type, passed: bool, with_annotation: bool = False):
    """Build a minimal in-memory DB with one requirement + SVC + MVR."""
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_T")
    svc_id = UrnId(urn="ms-001", id="SVC_T")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=impl_type,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc = SVCData(
        id=svc_id, title="S", verification=VERIFICATIONTYPES.MANUAL_TEST, revision="1.0.0", requirement_ids=[req_id]
    )
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    if with_annotation:
        db.insert_annotation_impl(
            req_id, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar")
        )
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="test_method")
    db.insert_annotation_test(svc_id, ann)
    status = TEST_RUN_STATUS.PASSED if passed else TEST_RUN_STATUS.FAILED
    db.insert_test_result("ms-001", "test_method", status)
    db.commit()
    return db, req_id


def test_meets_requirements_in_code_with_annotation_and_passing_tests():
    db, req_id = _make_db_with_req(IMPLEMENTATION.IN_CODE, passed=True, with_annotation=True)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["implementation"] == "in-code"
    assert result["meets_requirements"] is True
    db.close()


def test_meets_requirements_in_code_without_annotation_is_false():
    db, req_id = _make_db_with_req(IMPLEMENTATION.IN_CODE, passed=True, with_annotation=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["meets_requirements"] is False
    db.close()


@pytest.mark.parametrize(
    "impl_type",
    [
        IMPLEMENTATION.NOT_APPLICABLE,
        IMPLEMENTATION.CONFIGURATION,
        IMPLEMENTATION.PLATFORM,
        IMPLEMENTATION.FRAMEWORK,
    ],
)
def test_meets_requirements_non_code_type_passing_tests_true(impl_type):
    db, req_id = _make_db_with_req(impl_type, passed=True, with_annotation=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["implementation"] == impl_type.value
    assert result["meets_requirements"] is True
    db.close()


@pytest.mark.parametrize(
    "impl_type",
    [
        IMPLEMENTATION.NOT_APPLICABLE,
        IMPLEMENTATION.CONFIGURATION,
        IMPLEMENTATION.PLATFORM,
        IMPLEMENTATION.FRAMEWORK,
    ],
)
def test_meets_requirements_non_code_type_failing_tests_false(impl_type):
    db, req_id = _make_db_with_req(impl_type, passed=False, with_annotation=False)
    repo = RequirementsRepository(db)
    result = get_requirement_status(req_id.id, repo)
    assert result is not None
    assert result["meets_requirements"] is False
    db.close()


def test_get_requirements_status_all_mixed_types():
    """get_requirements_status_all returns correct meets_requirements for each impl type."""
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    URN = "ms-001"

    in_code_id = UrnId(urn=URN, id="REQ_CODE")
    cfg_id = UrnId(urn=URN, id="REQ_CFG")
    svc_code = UrnId(urn=URN, id="SVC_CODE")
    svc_cfg = UrnId(urn=URN, id="SVC_CFG")

    for req_id, impl_type in [(in_code_id, IMPLEMENTATION.IN_CODE), (cfg_id, IMPLEMENTATION.CONFIGURATION)]:
        req = RequirementData(
            id=req_id,
            title="T",
            significance=SIGNIFICANCETYPES.SHALL,
            description="D",
            implementation=impl_type,
            categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
            revision="1.0.0",
        )
        db.insert_requirement(req_id.urn, req)

    for svc_id, req_id in [(svc_code, in_code_id), (svc_cfg, cfg_id)]:
        svc = SVCData(
            id=svc_id, title="S", verification=VERIFICATIONTYPES.MANUAL_TEST, revision="1.0.0", requirement_ids=[req_id]
        )
        db.insert_svc(svc_id.urn, svc)
        ann = AnnotationData(element_kind="METHOD", fully_qualified_name=f"test_{svc_id.id}")
        db.insert_annotation_test(svc_id, ann)
        db.insert_test_result(URN, f"test_{svc_id.id}", TEST_RUN_STATUS.PASSED)

    db.insert_annotation_impl(in_code_id, AnnotationData(element_kind="METHOD", fully_qualified_name="com.Foo.bar"))
    db.commit()

    repo = RequirementsRepository(db)
    results = {r["id"]: r for r in get_requirements_status_all(repo)}

    assert results["REQ_CODE"]["meets_requirements"] is True
    assert results["REQ_CFG"]["meets_requirements"] is True
    db.close()


def test_get_requirements_status_all_in_code_without_annotation_false():
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")
    req_id = UrnId(urn="ms-001", id="REQ_NO_ANN")
    req = RequirementData(
        id=req_id,
        title="T",
        significance=SIGNIFICANCETYPES.SHALL,
        description="D",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        revision="1.0.0",
    )
    svc_id = UrnId(urn="ms-001", id="SVC_T")
    svc = SVCData(
        id=svc_id, title="S", verification=VERIFICATIONTYPES.MANUAL_TEST, revision="1.0.0", requirement_ids=[req_id]
    )
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="test_m")
    db.insert_requirement(req_id.urn, req)
    db.insert_svc(svc_id.urn, svc)
    db.insert_annotation_test(svc_id, ann)
    db.insert_test_result("ms-001", "test_m", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    results = {r["id"]: r for r in get_requirements_status_all(repo)}
    assert results["REQ_NO_ANN"]["meets_requirements"] is False
    db.close()


def test_get_requirements_status_all_urn_scoping():
    """get_requirements_status_all scoped to a URN excludes other URNs."""
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "ms-001")

    for urn, req_id_str in [("ms-001", "REQ_A"), ("ms-002", "REQ_B")]:
        req_id = UrnId(urn=urn, id=req_id_str)
        req = RequirementData(
            id=req_id,
            title="T",
            significance=SIGNIFICANCETYPES.SHALL,
            description="D",
            implementation=IMPLEMENTATION.IN_CODE,
            categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
            revision="1.0.0",
        )
        db.insert_requirement(req_id.urn, req)
    db.commit()

    repo = RequirementsRepository(db)
    scoped = get_requirements_status_all(repo, urn="ms-001")
    ids = {r["id"] for r in scoped}
    assert "REQ_A" in ids
    assert "REQ_B" not in ids
    db.close()
