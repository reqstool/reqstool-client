# Copyright © LFV

"""Full-text search over requirements, SVCs and MVRs, backed by an SQLite FTS5 index.

The index lives in the same in-memory database as the data and is filled from it, so it
always matches the loaded (and filtered) snapshot; a rebuilt snapshot gets a fresh index.
"""

import logging
import re
import sqlite3
from dataclasses import dataclass

from reqstool.storage.authorizer import authorizer
from reqstool.storage.database import RequirementsDatabase

logger = logging.getLogger(__name__)

SEARCH_TABLE = "search_fts"
# FTS5 keeps its index in these shadow tables; the authorizer must let queries read them.
SEARCH_SHADOW_TABLES = tuple(f"{SEARCH_TABLE}_{s}" for s in ("data", "idx", "content", "docsize", "config"))

KINDS = ("requirement", "svc", "mvr")

# One weight per column of the FTS table, in column order (unindexed ones are ignored).
_BM25_WEIGHTS = "0.0, 0.0, 0.0, 0.0, 10.0, 5.0, 2.0, 1.0"

_CREATE = f"""
CREATE VIRTUAL TABLE {SEARCH_TABLE} USING fts5(
    urn UNINDEXED, id_only UNINDEXED, kind UNINDEXED, lifecycle_state UNINDEXED,
    id, title, description, extra,
    tokenize = "porter unicode61 remove_diacritics 2 tokenchars '_'"
)
"""

_FILL = f"""
INSERT INTO {SEARCH_TABLE} (urn, id_only, kind, lifecycle_state, id, title, description, extra)
SELECT urn, id, 'requirement', lifecycle_state, id, title, description, rationale FROM requirements
UNION ALL
SELECT urn, id, 'svc', lifecycle_state, id, title, description, instructions FROM svcs
UNION ALL
SELECT urn, id, 'mvr', NULL, id, '', '', comment FROM mvrs
"""

_KIND_ORDER = "CASE kind WHEN 'requirement' THEN 0 WHEN 'svc' THEN 1 ELSE 2 END"


@dataclass(frozen=True)
class SearchHit:
    urn: str
    id: str
    kind: str
    snippet: str


def build_search_index(db: RequirementsDatabase) -> bool:
    """Create and fill the index from the database's current contents.

    Call after filters are applied so search sees what `status` sees. Returns False, leaving
    search to fall back to LIKE matching, if this SQLite build lacks FTS5.

    The authorizer is lifted for this fixed, parameterless DDL because FTS5 reads
    sqlite_master while creating its shadow tables; it is restored on every path.
    """
    conn = db.connection
    conn.set_authorizer(None)
    try:
        try:
            conn.execute(_CREATE)
        except sqlite3.OperationalError as exc:
            logger.warning("FTS5 unavailable, search falls back to unranked LIKE matching: %s", exc)
            return False
        conn.execute(_FILL)
        conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('search_index', 'fts5')")
        conn.commit()
        return True
    finally:
        conn.set_authorizer(authorizer)


def _tokens(query: str) -> list[str]:
    return re.findall(r"\w+", query)


def _fts_query(tokens: list[str]) -> str:
    # Every token is quoted (so user text can never be FTS5 syntax) and matches exactly (stemmed)
    # or as a prefix; tokens are ANDed.
    return " AND ".join(f'("{t}" OR "{t}"*)' for t in tokens)


def _has_index(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM metadata WHERE key = 'search_index' AND value = 'fts5'").fetchone() is not None


def search(
    db: RequirementsDatabase,
    query: str,
    kinds: list[str] | None = None,
    urn: str | None = None,
    lifecycle_state: str | None = None,
    limit: int = 20,
) -> tuple[list[SearchHit], bool]:
    """Ranked search. Returns (hits, ranked); ranked is False when the LIKE fallback answered.

    A lifecycle_state filter excludes MVRs, which have no lifecycle.
    """
    tokens = _tokens(query)
    if not tokens:
        return [], True

    conn = db.connection
    where, params = [], []
    if kinds:
        where.append(f"kind IN ({','.join('?' * len(kinds))})")
        params += kinds
    if urn:
        where.append("urn = ?")
        params.append(urn)
    if lifecycle_state:
        where.append("lifecycle_state = ?")
        params.append(lifecycle_state)

    if _has_index(conn):
        sql = (
            f"SELECT urn, id_only, kind, snippet({SEARCH_TABLE}, -1, '[', ']', '…', 12) AS snippet"
            f" FROM {SEARCH_TABLE} WHERE {SEARCH_TABLE} MATCH ?" + "".join(f" AND {w}" for w in where)
            # FTS5 scores are negative (lower is better); on small corpora many tie, so break ties
            # deterministically by kind and ID.
            + f" ORDER BY bm25({SEARCH_TABLE}, {_BM25_WEIGHTS}), {_KIND_ORDER}, id_only LIMIT ?"
        )
        rows = conn.execute(sql, [_fts_query(tokens), *params, limit]).fetchall()
        return [SearchHit(r["urn"], r["id_only"], r["kind"], _one_line(r["snippet"])) for r in rows], True

    return _like_search(conn, tokens, where, params, limit), False


def _like_search(conn, tokens, where, params, limit) -> list[SearchHit]:
    docs = (
        "SELECT urn, id, 'requirement' AS kind, lifecycle_state,"
        " id || ' ' || title || ' ' || description || ' ' || COALESCE(rationale, '') AS text FROM requirements"
        " UNION ALL SELECT urn, id, 'svc', lifecycle_state,"
        " id || ' ' || title || ' ' || COALESCE(description, '') || ' ' || COALESCE(instructions, '') FROM svcs"
        " UNION ALL SELECT urn, id, 'mvr', NULL, id || ' ' || COALESCE(comment, '') FROM mvrs"
    )
    like = " AND ".join("text LIKE ? ESCAPE '\\'" for _ in tokens)
    sql = (
        f"SELECT urn, id, kind, text FROM ({docs}) WHERE {like}"
        + "".join(f" AND {w}" for w in where)
        + f" ORDER BY {_KIND_ORDER}, id LIMIT ?"
    )
    rows = conn.execute(sql, [f"%{_like_escape(t)}%" for t in tokens] + params + [limit]).fetchall()
    return [SearchHit(r["urn"], r["id"], r["kind"], _snippet(r["text"], tokens[0])) for r in rows]


def _like_escape(token: str) -> str:
    """Make `%`, `_` and the escape character itself literal in a LIKE pattern (see ESCAPE '\\')."""
    return token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _snippet(text: str, token: str, width: int = 60) -> str:
    i = text.lower().find(token.lower())
    start = max(0, i - width // 2)
    end = start + width
    return ("…" if start else "") + _one_line(text[start:end]) + ("…" if len(text) > end else "")
