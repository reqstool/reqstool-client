import pytest
from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    RequirementData,
    MetaData,
    ReferenceData,
    VARIANTS,
)
from reqstool.models.svcs import SVCData, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository


URN = "ms-001"
REQ_ID = UrnId(urn=URN, id="REQ_001")
REQ_ID_2 = UrnId(urn=URN, id="REQ_002")
SVC_ID = UrnId(urn=URN, id="SVC_001")
SVC_ID_2 = UrnId(urn=URN, id="SVC_002")
MVR_ID = UrnId(urn=URN, id="MVR_001")


@pytest.fixture
def db():
    database = RequirementsDatabase()
    yield database
    database.close()


def _insert_requirement(db, urn_id=REQ_ID, implementation=IMPLEMENTATION.IN_CODE):
    req = RequirementData(
        id=urn_id,
        title="Requirement",
        significance=SIGNIFICANCETYPES.SHALL,
        description="Desc",
        rationale="Rationale",
        implementation=implementation,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        references=[ReferenceData(requirement_ids={UrnId(urn="sys-001", id="REQ_100")})],
        revision="1.0.0",
    )
    db.insert_requirement(urn_id.urn, req)
    return req


def _insert_svc(db, svc_id=SVC_ID, req_ids=None):
    svc = SVCData(
        id=svc_id,
        title="SVC",
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        revision="1.0.0",
        requirement_ids=req_ids or [REQ_ID],
    )
    db.insert_svc(svc_id.urn, svc)
    return svc


def _insert_mvr(db, mvr_id=MVR_ID, svc_ids=None, passed=True):
    mvr = MVRData(id=mvr_id, passed=passed, comment="OK", svc_ids=svc_ids or [SVC_ID])
    db.insert_mvr(mvr_id.urn, mvr)
    return mvr


def _setup_metadata(db, urn=URN):
    metadata = MetaData(urn=urn, variant=VARIANTS.MICROSERVICE, title="Test Service")
    db.insert_urn_metadata(metadata)
    db.set_metadata("initial_urn", urn)
    db.commit()


# -- Metadata queries --


def test_get_initial_urn(db):
    db.set_metadata("initial_urn", "ms-001")
    db.commit()
    repo = RequirementsRepository(db)
    assert repo.get_initial_urn() == "ms-001"


def test_get_urn_parsing_order(db):
    m1 = MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System")
    m2 = MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="MS")
    db.insert_urn_metadata(m1)
    db.insert_urn_metadata(m2)
    db.commit()

    repo = RequirementsRepository(db)
    assert repo.get_urn_parsing_order() == ["sys-001", "ms-001"]


def test_get_import_graph(db):
    _setup_metadata(db, "ms-001")
    m2 = MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System")
    db.insert_urn_metadata(m2)
    db.insert_parsing_graph_edge("ms-001", "sys-001")
    db.commit()

    repo = RequirementsRepository(db)
    graph = repo.get_import_graph()
    assert "sys-001" in graph["ms-001"]
    assert graph["sys-001"] == []


def test_is_filtered_false_by_default(db):
    repo = RequirementsRepository(db)
    assert repo.is_filtered() is False


def test_is_filtered_true(db):
    db.set_metadata("filtered", "true")
    db.commit()
    repo = RequirementsRepository(db)
    assert repo.is_filtered() is True


# -- Entity queries --


def test_get_all_requirements(db):
    _insert_requirement(db, REQ_ID)
    _insert_requirement(db, REQ_ID_2)
    db.commit()

    repo = RequirementsRepository(db)
    reqs = repo.get_all_requirements()
    assert len(reqs) == 2
    assert REQ_ID in reqs
    assert REQ_ID_2 in reqs
    assert reqs[REQ_ID].title == "Requirement"
    assert reqs[REQ_ID].significance == SIGNIFICANCETYPES.SHALL
    assert reqs[REQ_ID].implementation == IMPLEMENTATION.IN_CODE


def test_get_all_requirements_categories(db):
    _insert_requirement(db)
    db.commit()

    repo = RequirementsRepository(db)
    reqs = repo.get_all_requirements()
    assert CATEGORIES.FUNCTIONAL_SUITABILITY in reqs[REQ_ID].categories


def test_get_all_requirements_references(db):
    _insert_requirement(db)
    db.commit()

    repo = RequirementsRepository(db)
    reqs = repo.get_all_requirements()
    refs = reqs[REQ_ID].references
    assert len(refs) == 1
    assert UrnId(urn="sys-001", id="REQ_100") in refs[0].requirement_ids


def test_get_all_requirements_lifecycle(db):
    _insert_requirement(db)
    db.commit()

    repo = RequirementsRepository(db)
    reqs = repo.get_all_requirements()
    assert reqs[REQ_ID].lifecycle.state == LIFECYCLESTATE.EFFECTIVE


def test_get_all_requirements_empty(db):
    repo = RequirementsRepository(db)
    assert repo.get_all_requirements() == {}


def test_get_all_svcs(db):
    _insert_requirement(db)
    _insert_svc(db)
    db.commit()

    repo = RequirementsRepository(db)
    svcs = repo.get_all_svcs()
    assert len(svcs) == 1
    assert svcs[SVC_ID].title == "SVC"
    assert svcs[SVC_ID].verification == VERIFICATIONTYPES.AUTOMATED_TEST
    assert REQ_ID in svcs[SVC_ID].requirement_ids


def test_get_all_mvrs(db):
    _insert_requirement(db)
    _insert_svc(db)
    _insert_mvr(db)
    db.commit()

    repo = RequirementsRepository(db)
    mvrs = repo.get_all_mvrs()
    assert len(mvrs) == 1
    assert mvrs[MVR_ID].passed is True
    assert SVC_ID in mvrs[MVR_ID].svc_ids


# -- Index/lookup queries --


def test_get_svcs_for_req(db):
    _insert_requirement(db)
    _insert_svc(db, SVC_ID, req_ids=[REQ_ID])
    _insert_svc(db, SVC_ID_2, req_ids=[REQ_ID])
    db.commit()

    repo = RequirementsRepository(db)
    svcs = repo.get_svcs_for_req(REQ_ID)
    assert len(svcs) == 2
    assert SVC_ID in svcs
    assert SVC_ID_2 in svcs


def test_get_svcs_for_req_empty(db):
    _insert_requirement(db)
    db.commit()

    repo = RequirementsRepository(db)
    assert repo.get_svcs_for_req(REQ_ID) == []


def test_get_mvrs_for_svc(db):
    _insert_requirement(db)
    _insert_svc(db)
    _insert_mvr(db, MVR_ID, svc_ids=[SVC_ID])
    db.commit()

    repo = RequirementsRepository(db)
    mvrs = repo.get_mvrs_for_svc(SVC_ID)
    assert mvrs == [MVR_ID]


def test_get_annotations_impls(db):
    _insert_requirement(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar")
    db.insert_annotation_impl(REQ_ID, ann)
    db.commit()

    repo = RequirementsRepository(db)
    impls = repo.get_annotations_impls()
    assert REQ_ID in impls
    assert len(impls[REQ_ID]) == 1
    assert impls[REQ_ID][0].fully_qualified_name == "com.example.Foo.bar"


def test_get_annotations_tests(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.commit()

    repo = RequirementsRepository(db)
    tests = repo.get_annotations_tests()
    assert SVC_ID in tests
    assert tests[SVC_ID][0].element_kind == "METHOD"


def test_get_annotations_impls_for_req(db):
    _insert_requirement(db)
    ann1 = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar")
    ann2 = AnnotationData(element_kind="CLASS", fully_qualified_name="com.example.Baz")
    db.insert_annotation_impl(REQ_ID, ann1)
    db.insert_annotation_impl(REQ_ID, ann2)
    db.commit()

    repo = RequirementsRepository(db)
    impls = repo.get_annotations_impls_for_req(REQ_ID)
    assert len(impls) == 2
    fqns = {a.fully_qualified_name for a in impls}
    assert "com.example.Foo.bar" in fqns
    assert "com.example.Baz" in fqns


def test_get_annotations_tests_for_svc(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.commit()

    repo = RequirementsRepository(db)
    tests = repo.get_annotations_tests_for_svc(SVC_ID)
    assert len(tests) == 1
    assert tests[0].fully_qualified_name == "com.example.FooTest.testBar"


# -- Test result resolution --


def test_get_automated_test_results_method_passed(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_test_result(URN, "com.example.FooTest.testBar", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    results = repo.get_automated_test_results()
    key = UrnId(urn=URN, id="com.example.FooTest.testBar")
    assert key in results
    assert results[key][0].status == TEST_RUN_STATUS.PASSED


def test_get_automated_test_results_method_missing(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(SVC_ID, ann)
    db.commit()

    repo = RequirementsRepository(db)
    results = repo.get_automated_test_results()
    key = UrnId(urn=URN, id="com.example.FooTest.testBar")
    assert results[key][0].status == TEST_RUN_STATUS.MISSING


def test_get_automated_test_results_class_all_passed(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="CLASS", fully_qualified_name="com.example.FooTest")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_test_result(URN, "com.example.FooTest.testA", TEST_RUN_STATUS.PASSED)
    db.insert_test_result(URN, "com.example.FooTest.testB", TEST_RUN_STATUS.PASSED)
    db.commit()

    repo = RequirementsRepository(db)
    results = repo.get_automated_test_results()
    key = UrnId(urn=URN, id="com.example.FooTest")
    assert results[key][0].status == TEST_RUN_STATUS.PASSED


def test_get_automated_test_results_class_some_failed(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="CLASS", fully_qualified_name="com.example.FooTest")
    db.insert_annotation_test(SVC_ID, ann)
    db.insert_test_result(URN, "com.example.FooTest.testA", TEST_RUN_STATUS.PASSED)
    db.insert_test_result(URN, "com.example.FooTest.testB", TEST_RUN_STATUS.FAILED)
    db.commit()

    repo = RequirementsRepository(db)
    results = repo.get_automated_test_results()
    key = UrnId(urn=URN, id="com.example.FooTest")
    assert results[key][0].status == TEST_RUN_STATUS.FAILED


def test_get_automated_test_results_class_no_results(db):
    _insert_requirement(db)
    _insert_svc(db)
    ann = AnnotationData(element_kind="CLASS", fully_qualified_name="com.example.FooTest")
    db.insert_annotation_test(SVC_ID, ann)
    db.commit()

    repo = RequirementsRepository(db)
    results = repo.get_automated_test_results()
    key = UrnId(urn=URN, id="com.example.FooTest")
    assert results[key][0].status == TEST_RUN_STATUS.MISSING


# -- URN location queries --


def test_get_urn_location_with_values(db):
    metadata = MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Test")
    db.insert_urn_metadata(metadata, location_type="local", location_uri="file:///home/user/project/docs/reqstool")
    db.commit()

    repo = RequirementsRepository(db)
    loc = repo.get_urn_location("ms-001")
    assert loc is not None
    assert loc["type"] == "local"
    assert loc["uri"] == "file:///home/user/project/docs/reqstool"


def test_get_urn_location_no_values(db):
    metadata = MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Test")
    db.insert_urn_metadata(metadata)
    db.commit()

    repo = RequirementsRepository(db)
    loc = repo.get_urn_location("ms-001")
    assert loc is not None
    assert loc["type"] is None
    assert loc["uri"] is None


def test_get_urn_location_unknown_urn(db):
    repo = RequirementsRepository(db)
    assert repo.get_urn_location("nonexistent") is None
