# Copyright © LFV

import sqlite3

import pytest

from reqstool.storage.database import RequirementsDatabase


@pytest.fixture
def db():
    database = RequirementsDatabase()
    yield database
    database.close()


# -- Denied operations --


def test_attach_denied(db):
    with pytest.raises(sqlite3.DatabaseError):
        db.connection.execute("ATTACH DATABASE ':memory:' AS other")


def test_denied_pragma(db):
    with pytest.raises(sqlite3.DatabaseError):
        db.connection.execute("PRAGMA compile_options")


def test_create_unknown_table_denied(db):
    with pytest.raises(sqlite3.DatabaseError):
        db.connection.execute("CREATE TABLE evil (x TEXT)")


# -- Allowed operations --


def test_insert_known_table(db):
    db.connection.execute("INSERT INTO metadata (key, value) VALUES ('test', 'value')")
    db.connection.commit()
    row = db.connection.execute("SELECT value FROM metadata WHERE key = 'test'").fetchone()
    assert row["value"] == "value"


def test_select_known_table(db):
    rows = db.connection.execute("SELECT * FROM requirements").fetchall()
    assert len(rows) == 0


def test_foreign_keys_pragma_allowed(db):
    row = db.connection.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_delete_known_table(db):
    db.connection.execute("INSERT INTO metadata (key, value) VALUES ('test', 'value')")
    db.connection.commit()
    db.connection.execute("DELETE FROM metadata WHERE key = 'test'")
    db.connection.commit()
    count = db.connection.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
    assert count == 0
