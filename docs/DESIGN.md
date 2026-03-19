# Design: Graph Traversal and Data Ingestion

Captures architectural decisions for how `CombinedRawDatasetsGenerator` traverses the URN graph
and what data is inserted into SQLite for each node role.

Related code: `src/reqstool/model_generators/combined_raw_datasets_generator.py`,
`src/reqstool/storage/database_filter_processor.py`

---

## The graph

A reqstool graph is a directed graph of URNs connected by two edge types:

- **`import`** — "I reference requirements from this URN" (upward, toward requirement definitions)
- **`implementation`** — "this URN implements my requirements" (downward, toward evidence providers)

Example:

```
A1 (defines requirements)
  ← imported by B1
    ← imported by C1 (initial URN — the one being reported on)
      ← implemented by lib-a
        ← implemented by lib-b
          ← implemented by lib-c
```

---

## Two-phase traversal

### Phase 1 — import chain (DFS, recursive)

Traverses `imports:` sections recursively. For each node, all five data types are fully inserted:
`requirements`, `svcs`, `mvrs`, `annotations`, `test_results`.

Order: depth-first so ancestors are inserted before their children. This matters for FK constraints
(SVCs reference requirements that must exist first).

Cycle detection: visited set seeded with the initial URN. `CircularImportError` raised on re-entry.

### Phase 2 — implementation chain (recursive)

Traverses `implementations:` sections recursively. Think library-uses-library, not
system→microservice. lib-a can have its own implementations (lib-b → lib-c).

For each node:

| File | Action |
|------|--------|
| `requirements.yml` | Parse fully (validation runs); insert **metadata only** — skip `insert_requirement` |
| `svcs.yml` | Insert normally — FK on `req_urn/req_id` rejects rows referencing out-of-scope requirements |
| `mvrs.yml` | Insert normally — FK on `svc_urn/svc_id` rejects rows referencing out-of-scope SVCs |
| `annotations.yml` | Insert normally — FK on `req_urn/req_id` rejects out-of-scope rows |
| test results | Insert with explicit scope check — no FK, keyed by FQN |

Cycle detection: separate visited set. `CircularImplementationError` raised on re-entry.

Note: `imports:` sections of implementation nodes are NOT followed. An implementation's own imports
point to a different requirement scope.

---

## Post-parse cleanup

After both phases complete, `DatabaseFilterProcessor._remove_implementation_requirements()` deletes
requirement rows for nodes that are only reachable via `implementation` edges:

```sql
DELETE FROM requirements WHERE urn IN (
    SELECT DISTINCT child_urn FROM parsing_graph WHERE edge_type = 'implementation'
    EXCEPT
    SELECT DISTINCT child_urn FROM parsing_graph WHERE edge_type = 'import'
    EXCEPT
    SELECT value FROM metadata WHERE key = 'initial_urn'
)
```

CASCADE handles SVCs/MVRs/annotations that only linked to those deleted requirements.
SVCs/annotations that link to in-scope requirements (from Phase 1) survive.

**Why post-parse and not ingest-time?** ~30 lines in the filter processor vs ~150 lines
restructuring the generator and populator. The result is identical for an ephemeral in-memory DB.
The filter processor already runs a post-parse cleanup pass for user-defined `filters:` blocks —
adding structural cleanup there is consistent.

---

## Why recursive implementations?

The original design (pre-#324) treated implementations as leaf nodes based on the
system→microservice mental model. This was revised because:

- `variant` is no longer a behavioral gate (see #324)
- A library (`lib-a`) can depend on another library (`lib-b`) which itself has implementations
- All nodes in the implementation subtree can have annotations/tests pointing to in-scope requirements
- Flat traversal silently misses evidence from lib-b, lib-c, etc.

---

## Why `variant` is not a behavioral gate

Pre-#324, `variant: system/microservice/external` controlled which YAML sections were parsed and
which files were read. This was removed because:

- It encoded relationship role as an intrinsic property (a URN is not inherently a "microservice")
- It created a confusing 3×N matrix of allowed/disallowed sections
- It silently ignored files when the variant didn't match, causing hard-to-debug data loss
- Presence-based parsing is simpler, more predictable, and more general

`variant` remains in the schema as optional advisory metadata for display/tooling purposes.
