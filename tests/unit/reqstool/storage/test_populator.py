# Copyright © LFV

import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData, AnnotationsData
from reqstool.models.mvrs import MVRData, MVRsData
from reqstool.models.raw_datasets import RawDataset
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    VARIANTS,
    MetaData,
    ReferenceData,
    RequirementData,
    RequirementsData,
)
from reqstool.models.svcs import SVCData, SVCsData, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS, TestData, TestsData
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.populator import DatabasePopulator


@pytest.fixture
def db():
    database = RequirementsDatabase()
    yield database
    database.close()


@pytest.fixture
def raw_dataset():
    req_urn_id = UrnId(urn="ms-001", id="REQ_001")
    svc_urn_id = UrnId(urn="ms-001", id="SVC_001")
    mvr_urn_id = UrnId(urn="ms-001", id="MVR_001")
    test_urn_id = UrnId(urn="ms-001", id="com.example.FooTest.testBar")

    req = RequirementData(
        id=req_urn_id,
        title="Test requirement",
        significance=SIGNIFICANCETYPES.SHALL,
        description="A test requirement",
        rationale="For testing",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY],
        references=[ReferenceData(requirement_ids={UrnId(urn="sys-001", id="REQ_100")})],
        revision="1.0.0",
    )

    svc = SVCData(
        id=svc_urn_id,
        title="Test SVC",
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        revision="1.0.0",
        requirement_ids=[req_urn_id],
    )

    mvr = MVRData(
        id=mvr_urn_id,
        passed=True,
        comment="Verified",
        svc_ids=[svc_urn_id],
    )

    annotations = AnnotationsData(
        implementations={
            req_urn_id: [AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar")]
        },
        tests={svc_urn_id: [AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")]},
    )

    tests = TestsData(
        tests={test_urn_id: TestData(fully_qualified_name="com.example.FooTest.testBar", status=TEST_RUN_STATUS.PASSED)}
    )

    return RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Test Service"),
            requirements={req_urn_id: req},
        ),
        svcs_data=SVCsData(cases={svc_urn_id: svc}),
        mvrs_data=MVRsData(results={mvr_urn_id: mvr}),
        annotations_data=annotations,
        automated_tests=tests,
    )


def test_populate_requirements(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    count = db.connection.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
    assert count == 1

    row = db.connection.execute("SELECT * FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'").fetchone()
    assert row["title"] == "Test requirement"
    assert row["significance"] == "shall"


def test_populate_requirement_categories(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT category FROM requirement_categories").fetchall()
    assert len(rows) == 1
    assert rows[0]["category"] == "functional-suitability"


def test_populate_requirement_references(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT * FROM requirement_references").fetchall()
    assert len(rows) == 1
    assert rows[0]["ref_req_urn"] == "sys-001"
    assert rows[0]["ref_req_id"] == "REQ_100"


def test_populate_svcs(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    count = db.connection.execute("SELECT COUNT(*) FROM svcs").fetchone()[0]
    assert count == 1

    row = db.connection.execute("SELECT * FROM svcs WHERE urn = 'ms-001' AND id = 'SVC_001'").fetchone()
    assert row["verification_type"] == "automated-test"


def test_populate_svc_requirement_links(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT * FROM svc_requirement_links").fetchall()
    assert len(rows) == 1
    assert rows[0]["req_urn"] == "ms-001"
    assert rows[0]["req_id"] == "REQ_001"


def test_populate_mvrs(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    count = db.connection.execute("SELECT COUNT(*) FROM mvrs").fetchone()[0]
    assert count == 1

    row = db.connection.execute("SELECT * FROM mvrs WHERE urn = 'ms-001' AND id = 'MVR_001'").fetchone()
    assert row["passed"] == 1
    assert row["comment"] == "Verified"


def test_populate_mvr_svc_links(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT * FROM mvr_svc_links").fetchall()
    assert len(rows) == 1
    assert rows[0]["svc_urn"] == "ms-001"
    assert rows[0]["svc_id"] == "SVC_001"


def test_populate_annotations_impls(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT * FROM annotations_impls").fetchall()
    assert len(rows) == 1
    assert rows[0]["fqn"] == "com.example.Foo.bar"
    assert rows[0]["element_kind"] == "METHOD"


def test_populate_annotations_tests(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT * FROM annotations_tests").fetchall()
    assert len(rows) == 1
    assert rows[0]["fqn"] == "com.example.FooTest.testBar"


def test_populate_test_results(db, raw_dataset):
    DatabasePopulator.populate_from_raw_dataset(db, "ms-001", raw_dataset)

    rows = db.connection.execute("SELECT * FROM test_results").fetchall()
    assert len(rows) == 1
    assert rows[0]["fqn"] == "com.example.FooTest.testBar"
    assert rows[0]["status"] == "passed"


def test_populate_with_none_optional_fields(db):
    """Populate a RawDataset with only requirements (no svcs, mvrs, annotations, tests)."""
    req = RequirementData(
        id=UrnId(urn="ms-002", id="REQ_010"),
        title="Minimal",
        significance=SIGNIFICANCETYPES.MAY,
        description="Minimal req",
        revision="0.1.0",
    )
    rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-002", variant=VARIANTS.MICROSERVICE, title="Minimal Service"),
            requirements={UrnId(urn="ms-002", id="REQ_010"): req},
        ),
    )
    DatabasePopulator.populate_from_raw_dataset(db, "ms-002", rd)

    assert db.connection.execute("SELECT COUNT(*) FROM requirements").fetchone()[0] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM svcs").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM mvrs").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM annotations_impls").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM annotations_tests").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM test_results").fetchone()[0] == 0
