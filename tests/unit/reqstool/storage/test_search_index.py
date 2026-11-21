# Copyright © LFV

import sqlite3

import pytest

from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.search_index import build_search_index, search


def _req(db, urn, id, title, description, rationale=None, state="effective"):
    db.connection.execute(
        "INSERT INTO requirements (urn, id, title, significance, lifecycle_state, implementation, description,"
        " rationale, revision) VALUES (?, ?, ?, 'shall', ?, 'in-code', ?, ?, '1.0.0')",
        (urn, id, title, state, description, rationale),
    )


@pytest.fixture
def db():
    database = RequirementsDatabase()
    _req(database, "a", "REQ_PRIV_001", "Right to erasure", "Personal data shall be erased on request.")
    _req(database, "a", "REQ_PRIV_002", "Audit log", "All access is logged.", rationale="Needed to prove erasure")
    _req(database, "b", "REQ_X_001", "Retention", "Old data expires.", state="deprecated")
    database.connection.execute(
        "INSERT INTO svcs (urn, id, title, verification_type, lifecycle_state, description, instructions, revision)"
        " VALUES ('a', 'SVC_001', 'Erasure test', 'manual-test', 'effective', 'Verify erasure', 'Run the purge', '1')"
    )
    database.connection.execute("INSERT INTO mvrs (urn, id, passed, comment) VALUES ('a', 'MVR_001', 1, 'Erased ok')")
    assert build_search_index(database)
    yield database
    database.close()


def _ids(db, query, **kw):
    hits, ranked = search(db, query, **kw)
    assert ranked
    return [h.id for h in hits]


def test_stemming_matches_all_inflections_across_kinds(db):
    assert set(_ids(db, "erase")) == {"REQ_PRIV_001", "REQ_PRIV_002", "SVC_001", "MVR_001"}


def test_title_outranks_rationale(db):
    assert _ids(db, "erasure", kinds=["requirement"]) == ["REQ_PRIV_001", "REQ_PRIV_002"]


def test_id_is_matched_whole(db):
    assert _ids(db, "REQ_PRIV_002") == ["REQ_PRIV_002"]


def test_filters(db):
    assert _ids(db, "erasure", kinds=["svc"]) == ["SVC_001"]
    assert _ids(db, "data", urn="b") == ["REQ_X_001"]
    assert _ids(db, "data", lifecycle_state="deprecated") == ["REQ_X_001"]
    assert "MVR_001" not in _ids(db, "erase", lifecycle_state="effective")


def test_limit_and_empty_query(db):
    assert len(_ids(db, "erase", limit=2)) == 2
    assert search(db, "  !! ")[0] == []


def test_query_syntax_is_not_interpreted(db):
    search(db, 'erasure" OR NOT (')
    search(db, 'a" ) NEAR(')  # must not raise


def test_search_works_under_the_authorizer_and_stays_read_only(db):
    with pytest.raises(sqlite3.DatabaseError):
        db.connection.execute("CREATE VIRTUAL TABLE evil USING fts5(x)")
    with pytest.raises(sqlite3.DatabaseError):
        db.connection.execute("SELECT * FROM sqlite_master")


def test_falls_back_to_like_without_index():
    database = RequirementsDatabase()
    _req(database, "a", "REQ_001", "Right to erasure", "Data is erased.")
    hits, ranked = search(database, "erasure")
    assert not ranked and [h.id for h in hits] == ["REQ_001"]
    database.close()
