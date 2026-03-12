# Copyright © LFV

from reqstool.storage.el_compiler import ELToSQLCompiler


def test_compile_ids_equals_single():
    sql, params = ELToSQLCompiler.compile('ids == "REQ_001"', urn="ms-001")
    assert "IN (VALUES" in sql
    assert params == ["ms-001", "REQ_001"]


def test_compile_ids_equals_multiple():
    sql, params = ELToSQLCompiler.compile('ids == "REQ_001", "REQ_002"', urn="ms-001")
    assert "(?, ?), (?, ?)" in sql
    assert params == ["ms-001", "REQ_001", "ms-001", "REQ_002"]


def test_compile_ids_not_equals():
    sql, params = ELToSQLCompiler.compile('ids != "REQ_001"', urn="ms-001")
    assert "NOT IN" in sql
    assert params == ["ms-001", "REQ_001"]


def test_compile_ids_regex():
    sql, params = ELToSQLCompiler.compile("ids == /REQ_.*/", urn="ms-001")
    assert "regexp" in sql
    assert params == ["REQ_.*"]


def test_compile_and():
    sql, params = ELToSQLCompiler.compile('ids == "REQ_001" and ids == "REQ_002"', urn="ms-001")
    assert "AND" in sql
    assert len(params) == 4


def test_compile_or():
    sql, params = ELToSQLCompiler.compile('ids == "REQ_001" or ids == "REQ_002"', urn="ms-001")
    assert "OR" in sql
    assert len(params) == 4


def test_compile_not():
    sql, params = ELToSQLCompiler.compile('not ids == "REQ_001"', urn="ms-001")
    assert "NOT" in sql
    assert params == ["ms-001", "REQ_001"]


def test_compile_parentheses():
    sql, params = ELToSQLCompiler.compile('(ids == "REQ_001" or ids == "REQ_002") and ids != "REQ_003"', urn="ms-001")
    assert "AND" in sql
    assert "OR" in sql
    assert len(params) == 6


def test_compile_qualified_urn_id():
    sql, params = ELToSQLCompiler.compile('ids == "sys-001:REQ_050"', urn="ms-001")
    assert params == ["sys-001", "REQ_050"]
