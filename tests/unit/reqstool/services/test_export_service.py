import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    MetaData,
    ReferenceData,
    RequirementData,
    VARIANTS,
)
from reqstool.models.svcs import SVCData, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.services.export_service import ExportService
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository


URN = "ms-001"
REQ_ID = UrnId(urn=URN, id="REQ_001")
REQ_ID_2 = UrnId(urn=URN, id="REQ_002")
SVC_ID = UrnId(urn=URN, id="SVC_001")
SVC_ID_2 = UrnId(urn=URN, id="SVC_002")
MVR_ID = UrnId(urn=URN, id="MVR_001")


@pytest.fixture
def populated_db():
    db = RequirementsDatabase()
    metadata = MetaData(urn=URN, variant=VARIANTS.MICROSERVICE, title="Test Service")
    db.insert_urn_metadata(metadata)
    db.set_metadata("initial_urn", URN)

    req1 = RequirementData(
        id=REQ_ID,
        title="First Requirement",
        significance=SIGNIFICANCETYPES.SHALL,
        description="Desc 1",
        rationale="Rationale 1",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        references=[ReferenceData(requirement_ids={UrnId(urn="sys-001", id="REQ_100")})],
        revision="1.0.0",
    )
    req2 = RequirementData(
        id=REQ_ID_2,
        title="Second Requirement",
        significance=SIGNIFICANCETYPES.SHOULD,
        description="Desc 2",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.SECURITY],
        revision="2.0.0",
    )
    db.insert_requirement(URN, req1)
    db.insert_requirement(URN, req2)

    svc1 = SVCData(
        id=SVC_ID,
        title="SVC 1",
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        revision="1.0.0",
        requirement_ids=[REQ_ID],
    )
    svc2 = SVCData(
        id=SVC_ID_2,
        title="SVC 2",
        verification=VERIFICATIONTYPES.MANUAL_TEST,
        revision="1.0.0",
        requirement_ids=[REQ_ID_2],
    )
    db.insert_svc(URN, svc1)
    db.insert_svc(URN, svc2)

    mvr = MVRData(id=MVR_ID, passed=True, comment="Verified", svc_ids=[SVC_ID_2])
    db.insert_mvr(URN, mvr)

    db.insert_annotation_impl(REQ_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"))
    db.insert_annotation_test(
        SVC_ID, AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    )
    db.insert_test_result(URN, "com.example.FooTest.testBar", TEST_RUN_STATUS.PASSED)

    db.commit()
    yield db
    db.close()


def test_export_dict_top_level_keys(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    assert "metadata" in result
    assert "requirements" in result
    assert "svcs" in result
    assert "mvrs" in result
    assert "annotations" in result
    assert "test_results" in result


def test_export_dict_metadata(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    assert result["metadata"]["initial_urn"] == URN
    assert isinstance(result["metadata"]["urn_parsing_order"], list)
    assert isinstance(result["metadata"]["import_graph"], dict)


def test_export_dict_requirements(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    assert len(result["requirements"]) == 2
    req_key = str(REQ_ID)
    assert req_key in result["requirements"]
    req = result["requirements"][req_key]
    assert req["title"] == "First Requirement"
    assert req["significance"] == "shall"
    assert req["implementation_type"] == "in-code"
    assert "references" in req


def test_export_dict_svcs(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    assert len(result["svcs"]) == 2
    svc = result["svcs"][str(SVC_ID)]
    assert svc["verification"] == "automated-test"
    assert str(REQ_ID) in svc["requirement_ids"]


def test_export_dict_mvrs(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    assert len(result["mvrs"]) == 1
    mvr = result["mvrs"][str(MVR_ID)]
    assert mvr["passed"] is True
    assert mvr["comment"] == "Verified"


def test_export_dict_annotations(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    impls = result["annotations"]["implementations"]
    assert str(REQ_ID) in impls

    tests = result["annotations"]["tests"]
    assert str(SVC_ID) in tests


def test_export_dict_test_results(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict()

    assert len(result["test_results"]) > 0


# -- Filtering by req_ids --


def test_export_filter_by_req_ids(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict(req_ids=["REQ_001"])

    assert len(result["requirements"]) == 1
    assert str(REQ_ID) in result["requirements"]
    # SVC_001 linked to REQ_001 should be included
    assert str(SVC_ID) in result["svcs"]
    # SVC_002 linked only to REQ_002 should be excluded
    assert str(SVC_ID_2) not in result["svcs"]


# -- Filtering by svc_ids --


def test_export_filter_by_svc_ids(populated_db):
    repo = RequirementsRepository(populated_db)
    result = ExportService(repo).to_export_dict(svc_ids=["SVC_002"])

    assert str(SVC_ID_2) in result["svcs"]
    # REQ_002 is referenced by SVC_002, should be included
    assert str(REQ_ID_2) in result["requirements"]
    # MVR_001 linked to SVC_002 should be included
    assert str(MVR_ID) in result["mvrs"]


# -- Empty database --


def test_export_empty_database():
    db = RequirementsDatabase()
    db.set_metadata("initial_urn", "empty")
    m = MetaData(urn="empty", variant=VARIANTS.MICROSERVICE, title="Empty")
    db.insert_urn_metadata(m)
    db.commit()

    repo = RequirementsRepository(db)
    result = ExportService(repo).to_export_dict()

    assert result["requirements"] == {}
    assert result["svcs"] == {}
    assert result["mvrs"] == {}
    db.close()
