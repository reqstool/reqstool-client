## Why

An MCP client that does not know a requirement or SVC ID has no way to find one: the list tools
return everything and leave filtering to the caller. Issue #493 asks for ranked free-text search
over requirements, SVCs and MVRs.

## What Changes

- Add an MCP `search` tool backed by an SQLite FTS5 index (BM25-ranked, stemmed, prefix matching)
  over requirement IDs, titles, descriptions and rationale, SVC IDs, titles, descriptions and
  instructions, and MVR comments.
- The index is built in the same in-memory database after filtering, so it always matches the
  loaded snapshot and is rebuilt on every reload.
- Hits are filterable by kind, URN and lifecycle state; invalid `kinds`, `lifecycle_state` and
  unknown `urn` are errors rather than silently empty results.
- Requirement hits carry `completed`, taken from `compute_requirement_status` (the single
  verdict computation; see `consolidate-requirement-verdict`), never re-derived.
- Falls back to unranked LIKE matching, flagged by a `note`, when the Python build lacks FTS5.
- ID search is prefix-only (IDs are single tokens); this is documented, not a trigram index.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `mcp`: adds `MCP_0009`, an MCP search tool that ranks free-text matches over requirements, SVCs
  and MVRs, filterable by kind, URN and lifecycle state, reporting the shared completion verdict
  for requirement hits, from an index that always reflects the loaded snapshot.

## Impact

- `src/reqstool/storage/search_index.py`, `common/queries/search.py`, `mcp/server.py`,
  `common/project_session.py`, `storage/authorizer.py` (FTS5 shadow tables allowed).
- reqstool SSOT: `MCP_0009` and `SVC_MCP_0009`.
- MCP clients gain a `search` tool; no existing tool output changes.
