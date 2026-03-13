# Copyright © LFV

import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    VARIANTS,
    MetaData,
    ReferenceData,
    RequirementData,
)
from reqstool.models.svcs import SVCData, VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.storage.database import RequirementsDatabase


@pytest.fixture
def db():
    database = RequirementsDatabase()
    yield database
    database.close()


@pytest.fixture
def sample_requirement():
    return RequirementData(
        id=UrnId(urn="ms-001", id="REQ_001"),
        title="Test requirement",
        significance=SIGNIFICANCETYPES.SHALL,
        description="A test requirement",
        rationale="For testing",
        implementation=IMPLEMENTATION.IN_CODE,
        categories=[CATEGORIES.FUNCTIONAL_SUITABILITY, CATEGORIES.SECURITY],
        references=[ReferenceData(requirement_ids={UrnId(urn="sys-001", id="REQ_100")})],
        revision="1.0.0",
    )


@pytest.fixture
def sample_svc():
    return SVCData(
        id=UrnId(urn="ms-001", id="SVC_001"),
        title="Test SVC",
        description="A test SVC",
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        instructions="Run the tests",
        revision="1.0.0",
        requirement_ids=[UrnId(urn="ms-001", id="REQ_001")],
    )


@pytest.fixture
def sample_mvr():
    return MVRData(
        id=UrnId(urn="ms-001", id="MVR_001"),
        passed=True,
        comment="All good",
        svc_ids=[UrnId(urn="ms-001", id="SVC_001")],
    )


# -- Schema creation --


def test_all_tables_queryable(db):
    """Verify all expected tables exist by querying them."""
    tables = [
        "requirements",
        "requirement_categories",
        "requirement_references",
        "svcs",
        "svc_requirement_links",
        "mvrs",
        "mvr_svc_links",
        "annotations_impls",
        "annotations_tests",
        "test_results",
        "parsing_graph",
        "urn_metadata",
        "metadata",
    ]
    for table in tables:
        rows = db.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
        assert rows[0] == 0


def test_foreign_keys_enabled(db):
    row = db.connection.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


# -- Insert requirement --


def test_insert_requirement(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)

    row = db.connection.execute("SELECT * FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'").fetchone()
    assert row is not None
    assert row["title"] == "Test requirement"
    assert row["significance"] == "shall"
    assert row["lifecycle_state"] == "effective"
    assert row["lifecycle_reason"] is None
    assert row["implementation"] == "in-code"
    assert row["description"] == "A test requirement"
    assert row["rationale"] == "For testing"
    assert row["revision"] == "1.0.0"


def test_insert_requirement_categories(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)

    rows = db.connection.execute(
        "SELECT category FROM requirement_categories WHERE req_urn = 'ms-001' AND req_id = 'REQ_001'"
    ).fetchall()
    categories = {row["category"] for row in rows}
    assert categories == {"functional-suitability", "security"}


def test_insert_requirement_references(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)

    rows = db.connection.execute(
        "SELECT ref_req_urn, ref_req_id FROM requirement_references" " WHERE req_urn = 'ms-001' AND req_id = 'REQ_001'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["ref_req_urn"] == "sys-001"
    assert rows[0]["ref_req_id"] == "REQ_100"


def test_insert_requirement_no_categories_no_references(db):
    req = RequirementData(
        id=UrnId(urn="ms-001", id="REQ_002"),
        title="Minimal req",
        significance=SIGNIFICANCETYPES.MAY,
        description="Minimal",
        revision="0.1.0",
    )
    db.insert_requirement("ms-001", req)

    row = db.connection.execute("SELECT * FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_002'").fetchone()
    assert row is not None
    assert row["rationale"] is None

    cat_count = db.connection.execute(
        "SELECT COUNT(*) FROM requirement_categories WHERE req_urn = 'ms-001' AND req_id = 'REQ_002'"
    ).fetchone()[0]
    assert cat_count == 0


def test_insert_duplicate_requirement_raises(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)
    with pytest.raises(Exception):
        db.insert_requirement("ms-001", sample_requirement)


# -- Insert SVC --


def test_insert_svc(db, sample_requirement, sample_svc):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)

    row = db.connection.execute("SELECT * FROM svcs WHERE urn = 'ms-001' AND id = 'SVC_001'").fetchone()
    assert row is not None
    assert row["title"] == "Test SVC"
    assert row["verification_type"] == "automated-test"
    assert row["revision"] == "1.0.0"


def test_insert_svc_requirement_links(db, sample_requirement, sample_svc):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)

    rows = db.connection.execute(
        "SELECT req_urn, req_id FROM svc_requirement_links WHERE svc_urn = 'ms-001' AND svc_id = 'SVC_001'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["req_urn"] == "ms-001"
    assert rows[0]["req_id"] == "REQ_001"


# -- Insert MVR --


def test_insert_mvr(db, sample_requirement, sample_svc, sample_mvr):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)
    db.insert_mvr("ms-001", sample_mvr)

    row = db.connection.execute("SELECT * FROM mvrs WHERE urn = 'ms-001' AND id = 'MVR_001'").fetchone()
    assert row is not None
    assert row["passed"] == 1
    assert row["comment"] == "All good"


def test_insert_mvr_svc_links(db, sample_requirement, sample_svc, sample_mvr):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)
    db.insert_mvr("ms-001", sample_mvr)

    rows = db.connection.execute(
        "SELECT svc_urn, svc_id FROM mvr_svc_links WHERE mvr_urn = 'ms-001' AND mvr_id = 'MVR_001'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["svc_urn"] == "ms-001"
    assert rows[0]["svc_id"] == "SVC_001"


# -- Insert annotations --


def test_insert_annotation_impl(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)
    annotation = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar")
    db.insert_annotation_impl(UrnId(urn="ms-001", id="REQ_001"), annotation)

    rows = db.connection.execute("SELECT * FROM annotations_impls").fetchall()
    assert len(rows) == 1
    assert rows[0]["fqn"] == "com.example.Foo.bar"
    assert rows[0]["element_kind"] == "METHOD"


def test_insert_annotation_test(db, sample_requirement, sample_svc):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)
    annotation = AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar")
    db.insert_annotation_test(UrnId(urn="ms-001", id="SVC_001"), annotation)

    rows = db.connection.execute("SELECT * FROM annotations_tests").fetchall()
    assert len(rows) == 1
    assert rows[0]["fqn"] == "com.example.FooTest.testBar"


# -- Insert test result --


def test_insert_test_result(db):
    db.insert_test_result("ms-001", "com.example.FooTest.testBar", TEST_RUN_STATUS.PASSED)

    row = db.connection.execute(
        "SELECT * FROM test_results WHERE urn = 'ms-001' AND fqn = 'com.example.FooTest.testBar'"
    ).fetchone()
    assert row is not None
    assert row["status"] == "passed"


# -- Parsing graph --


def test_insert_parsing_graph_edge(db):
    db.insert_parsing_graph_edge("sys-001", "ms-001")
    db.insert_parsing_graph_edge("sys-001", "ms-002")

    rows = db.connection.execute("SELECT child_urn FROM parsing_graph WHERE parent_urn = 'sys-001'").fetchall()
    children = {row["child_urn"] for row in rows}
    assert children == {"ms-001", "ms-002"}


def test_insert_duplicate_parsing_graph_edge_ignored(db):
    db.insert_parsing_graph_edge("sys-001", "ms-001")
    db.insert_parsing_graph_edge("sys-001", "ms-001")

    count = db.connection.execute("SELECT COUNT(*) FROM parsing_graph").fetchone()[0]
    assert count == 1


# -- URN metadata --


def test_insert_urn_metadata_auto_increments_parse_position(db):
    db.insert_urn_metadata(MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System", url=None))
    db.insert_urn_metadata(
        MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Service", url="https://example.com")
    )

    rows = db.connection.execute("SELECT urn, parse_position FROM urn_metadata ORDER BY parse_position").fetchall()
    assert len(rows) == 2
    assert rows[0]["urn"] == "sys-001"
    assert rows[0]["parse_position"] == 0
    assert rows[1]["urn"] == "ms-001"
    assert rows[1]["parse_position"] == 1


# -- Metadata --


def test_set_and_get_metadata(db):
    db.set_metadata("initial_urn", "ms-001")
    assert db.get_metadata("initial_urn") == "ms-001"


def test_get_missing_metadata_returns_none(db):
    assert db.get_metadata("nonexistent") is None


def test_set_metadata_overwrites(db):
    db.set_metadata("filtered", "false")
    db.set_metadata("filtered", "true")
    assert db.get_metadata("filtered") == "true"


# -- CHECK constraints --


def test_check_constraint_rejects_invalid_significance(db):
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO requirements (urn, id, title, significance, lifecycle_state,"
            " implementation, description, revision)"
            " VALUES ('x', 'x', 'x', 'invalid', 'effective', 'in-code', 'x', '1.0.0')"
        )


def test_check_constraint_rejects_invalid_lifecycle_state(db):
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO requirements (urn, id, title, significance, lifecycle_state,"
            " implementation, description, revision)"
            " VALUES ('x', 'x', 'x', 'shall', 'invalid', 'in-code', 'x', '1.0.0')"
        )


def test_check_constraint_rejects_invalid_implementation(db):
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO requirements (urn, id, title, significance, lifecycle_state,"
            " implementation, description, revision)"
            " VALUES ('x', 'x', 'x', 'shall', 'effective', 'invalid', 'x', '1.0.0')"
        )


def test_check_constraint_rejects_invalid_category(db):
    db.connection.execute(
        "INSERT INTO requirements (urn, id, title, significance, lifecycle_state,"
        " implementation, description, revision)"
        " VALUES ('x', 'x', 'x', 'shall', 'effective', 'in-code', 'x', '1.0.0')"
    )
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO requirement_categories (req_urn, req_id, category) VALUES ('x', 'x', 'invalid')"
        )


def test_check_constraint_rejects_invalid_verification_type(db):
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO svcs (urn, id, title, verification_type, lifecycle_state, revision)"
            " VALUES ('x', 'x', 'x', 'invalid', 'effective', '1.0.0')"
        )


def test_check_constraint_rejects_invalid_test_status(db):
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute("INSERT INTO test_results (urn, fqn, status) VALUES ('x', 'x', 'invalid')")


def test_check_constraint_rejects_invalid_variant(db):
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO urn_metadata (urn, variant, title, parse_position) VALUES ('x', 'invalid', 'x', 0)"
        )


def test_check_constraint_rejects_invalid_element_kind(db):
    db.connection.execute(
        "INSERT INTO requirements (urn, id, title, significance, lifecycle_state,"
        " implementation, description, revision)"
        " VALUES ('x', 'x', 'x', 'shall', 'effective', 'in-code', 'x', '1.0.0')"
    )
    with pytest.raises(Exception, match="CHECK"):
        db.connection.execute(
            "INSERT INTO annotations_impls (req_urn, req_id, element_kind, fqn) VALUES ('x', 'x', 'INVALID', 'x')"
        )


# -- CASCADE delete --


def test_delete_requirement_cascades_to_categories(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)
    db.connection.execute("DELETE FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'")
    db.connection.commit()

    count = db.connection.execute("SELECT COUNT(*) FROM requirement_categories").fetchone()[0]
    assert count == 0


def test_delete_requirement_cascades_to_references(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)
    db.connection.execute("DELETE FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'")
    db.connection.commit()

    count = db.connection.execute("SELECT COUNT(*) FROM requirement_references").fetchone()[0]
    assert count == 0


def test_delete_requirement_cascades_to_svc_links(db, sample_requirement, sample_svc):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)

    db.connection.execute("DELETE FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'")
    db.connection.commit()

    count = db.connection.execute("SELECT COUNT(*) FROM svc_requirement_links").fetchone()[0]
    assert count == 0


def test_delete_requirement_cascades_to_annotations_impls(db, sample_requirement):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_annotation_impl(
        UrnId(urn="ms-001", id="REQ_001"),
        AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"),
    )

    db.connection.execute("DELETE FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'")
    db.connection.commit()

    count = db.connection.execute("SELECT COUNT(*) FROM annotations_impls").fetchone()[0]
    assert count == 0


def test_delete_svc_cascades_to_mvr_links(db, sample_requirement, sample_svc, sample_mvr):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)
    db.insert_mvr("ms-001", sample_mvr)

    db.connection.execute("DELETE FROM svcs WHERE urn = 'ms-001' AND id = 'SVC_001'")
    db.connection.commit()

    count = db.connection.execute("SELECT COUNT(*) FROM mvr_svc_links").fetchone()[0]
    assert count == 0


def test_delete_svc_cascades_to_annotations_tests(db, sample_requirement, sample_svc):
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)
    db.insert_annotation_test(
        UrnId(urn="ms-001", id="SVC_001"),
        AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.FooTest.testBar"),
    )

    db.connection.execute("DELETE FROM svcs WHERE urn = 'ms-001' AND id = 'SVC_001'")
    db.connection.commit()

    count = db.connection.execute("SELECT COUNT(*) FROM annotations_tests").fetchone()[0]
    assert count == 0


def test_full_cascade_chain(db, sample_requirement, sample_svc, sample_mvr):
    """Delete a requirement and verify cascade: req → categories, references, svc_links, annotations.
    SVCs and MVRs themselves are NOT deleted — only their links to the deleted requirement."""
    db.insert_requirement("ms-001", sample_requirement)
    db.insert_svc("ms-001", sample_svc)
    db.insert_mvr("ms-001", sample_mvr)
    db.insert_annotation_impl(
        UrnId(urn="ms-001", id="REQ_001"),
        AnnotationData(element_kind="METHOD", fully_qualified_name="com.example.Foo.bar"),
    )

    db.connection.execute("DELETE FROM requirements WHERE urn = 'ms-001' AND id = 'REQ_001'")
    db.connection.commit()

    assert db.connection.execute("SELECT COUNT(*) FROM requirement_categories").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM requirement_references").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM svc_requirement_links").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM annotations_impls").fetchone()[0] == 0
    # SVCs and MVRs themselves remain — only their links to the deleted requirement are gone
    assert db.connection.execute("SELECT COUNT(*) FROM svcs").fetchone()[0] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM mvrs").fetchone()[0] == 1
