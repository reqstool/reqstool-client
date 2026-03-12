# Copyright © LFV

import sqlite3

_ALLOWED_TABLES = frozenset(
    {
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
    }
)

_DENIED_PRAGMAS = frozenset(
    {
        "compile_options",
        "database_list",
        "module_list",
    }
)


def authorizer(action_code: int, arg1, arg2, db_name, trigger_name) -> int:
    if action_code == sqlite3.SQLITE_ATTACH:
        return sqlite3.SQLITE_DENY

    if action_code == sqlite3.SQLITE_PRAGMA:
        if arg1 in _DENIED_PRAGMAS:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    if action_code in (
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_SELECT,
    ):
        if arg1 is not None and arg1 not in _ALLOWED_TABLES:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    if action_code in (
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
        sqlite3.SQLITE_FUNCTION,
    ):
        return sqlite3.SQLITE_OK

    return sqlite3.SQLITE_DENY
