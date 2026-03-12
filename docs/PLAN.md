# Plan: #313 — Replace intermediate data structures with in-memory SQLite

## Context

The current pipeline: `Location → RawDataset → CombinedRawDataset → CombinedIndexedDataset → StatisticsContainer → Commands`

**Goal**: Eliminate `CombinedRawDataset`, `CombinedIndexedDataset`, and `StatisticsContainer` entirely. Replace with in-memory SQLite as single source of truth. Commands query the DB directly — no transitional bridge, no CID materialization.

The parser keeps producing per-URN `RawDataset` (useful for Pydantic validation), but feeds each one into SQLite immediately instead of collecting into `CombinedRawDataset`.

**End state**: `Location → parse → RawDataset (transient) → INSERT into SQLite → commands query DB`

---

## Phase 1: SQLite infrastructure — schema, database class, security

**Goal**: Foundation. Pure addition, zero risk.

**New files**:
| File | Purpose |
|---|---|
| `src/reqstool/storage/__init__.py` | Package init |
| `src/reqstool/storage/schema.py` | SQL DDL constants |
| `src/reqstool/storage/authorizer.py` | sqlite3 authorizer callback |
| `src/reqstool/storage/database.py` | `RequirementsDatabase` class |
| `tests/unit/reqstool/storage/__init__.py` | Test package init |
| `tests/unit/reqstool/storage/test_database.py` | Schema creation, insert/query round-trip, FK cascade |
| `tests/unit/reqstool/storage/test_authorizer.py` | Verify denied operations |

**SQLite schema**:
```sql
-- Core entities
requirements (urn TEXT, id TEXT, title TEXT, significance TEXT, lifecycle_state TEXT,
              lifecycle_reason TEXT, implementation TEXT, description TEXT,
              rationale TEXT, revision TEXT,  -- stored as "1.0.0", reconstruct via Version()
              PK(urn, id))
requirement_categories (req_urn TEXT, req_id TEXT, category TEXT,
              PK(req_urn, req_id, category),
              FK(req_urn, req_id) → requirements ON DELETE CASCADE)
requirement_references (req_urn TEXT, req_id TEXT, ref_req_urn TEXT, ref_req_id TEXT,
              PK(req_urn, req_id, ref_req_urn, ref_req_id),
              FK(req_urn, req_id) → requirements ON DELETE CASCADE)
              -- Flattened: YAML schema allows one references object per req;
              -- parser always creates exactly one ReferenceData per req.
svcs (urn TEXT, id TEXT, title TEXT, verification_type TEXT, lifecycle_state TEXT,
      lifecycle_reason TEXT, description TEXT, instructions TEXT, revision TEXT,
      PK(urn, id))
svc_requirement_links (svc_urn TEXT, svc_id TEXT, req_urn TEXT, req_id TEXT,
              PK(svc_urn, svc_id, req_urn, req_id),
              FK(svc_urn, svc_id) → svcs ON DELETE CASCADE,
              FK(req_urn, req_id) → requirements ON DELETE CASCADE)
mvrs (urn TEXT, id TEXT, passed INTEGER, comment TEXT,
      PK(urn, id))
mvr_svc_links (mvr_urn TEXT, mvr_id TEXT, svc_urn TEXT, svc_id TEXT,
              PK(mvr_urn, mvr_id, svc_urn, svc_id),
              FK(mvr_urn, mvr_id) → mvrs ON DELETE CASCADE,
              FK(svc_urn, svc_id) → svcs ON DELETE CASCADE)
annotations_impls (req_urn TEXT, req_id TEXT, element_kind TEXT, fqn TEXT,
              FK(req_urn, req_id) → requirements ON DELETE CASCADE)
annotations_tests (svc_urn TEXT, svc_id TEXT, element_kind TEXT, fqn TEXT,
              FK(svc_urn, svc_id) → svcs ON DELETE CASCADE)
test_results (urn TEXT, fqn TEXT, status TEXT,
              PK(urn, fqn))  -- one result per URN+FQN

-- Import DAG
parsing_graph (parent_urn TEXT, child_urn TEXT,
              PK(parent_urn, child_urn))

-- Per-URN metadata + parsing order (one row per parsed URN)
urn_metadata (urn TEXT PK, variant TEXT, title TEXT, url TEXT,
              parse_position INTEGER NOT NULL UNIQUE)

-- Scalar metadata (initial_urn, filtered flag)
metadata (key TEXT PK, value TEXT)

-- FK indexes (for integrity + performance)
CREATE INDEX idx_req_categories_fk ON requirement_categories(req_urn, req_id);
CREATE INDEX idx_req_references_fk ON requirement_references(req_urn, req_id);
CREATE INDEX idx_svc_req_links_svc ON svc_requirement_links(svc_urn, svc_id);
CREATE INDEX idx_svc_req_links_req ON svc_requirement_links(req_urn, req_id);
CREATE INDEX idx_mvr_svc_links_mvr ON mvr_svc_links(mvr_urn, mvr_id);
CREATE INDEX idx_mvr_svc_links_svc ON mvr_svc_links(svc_urn, svc_id);
CREATE INDEX idx_annotations_impls_fk ON annotations_impls(req_urn, req_id);
CREATE INDEX idx_annotations_tests_fk ON annotations_tests(svc_urn, svc_id);
CREATE INDEX idx_parsing_graph_parent ON parsing_graph(parent_urn);
CREATE INDEX idx_parsing_graph_child ON parsing_graph(child_urn);
```

**Note — no `filters` table**: Filters are applied during processing (Phase 3) to DELETE
filtered-out rows. The filter definitions themselves are read from the transient `RawDataset`
and applied as SQL DELETEs; they are not persisted in the DB.

**Metadata storage strategy**:
- `initial_urn` → `metadata` table: `INSERT INTO metadata VALUES ('initial_urn', 'ms-001')`
- `filtered` → `metadata` table: `INSERT INTO metadata VALUES ('filtered', 'true')`
- `urn_parsing_order` → `urn_metadata.parse_position` column: `SELECT urn FROM urn_metadata ORDER BY parse_position`
- `import_graph` → `parsing_graph` table (DAG edges)
- Per-URN variant/title/url → `urn_metadata` table (same row as parse_position)

**Authorizer**: Deny `ATTACH`, `LOAD_EXTENSION`, dangerous PRAGMAs. Allow DML on known tables.

**`RequirementsDatabase` insert API**:
- `insert_requirement(urn, req: RequirementData)` — inserts into requirements + requirement_categories + requirement_references
- `insert_svc(urn, svc: SVCData)` — inserts into svcs + svc_requirement_links
- `insert_mvr(urn, mvr: MVRData)` — inserts into mvrs + mvr_svc_links
- `insert_annotation_impl(req_urn_id, annotation: AnnotationData)`
- `insert_annotation_test(svc_urn_id, annotation: AnnotationData)`
- `insert_test_result(urn, fqn, status)`
- `insert_parsing_graph_edge(parent_urn, child_urn)`
- `insert_urn_metadata(urn, variant, title, url)` — auto-assigns next `parse_position`
- `set_metadata(key, value)` / `get_metadata(key)`

---

## Phase 2: Populator + parser integration — eliminate CombinedRawDataset

**Goal**: `CombinedRawDatasetsGenerator` takes a `RequirementsDatabase`, inserts each parsed `RawDataset` into it. `CombinedRawDataset` is deleted.

**New file**:
| File | Purpose |
|---|---|
| `src/reqstool/storage/populator.py` | `DatabasePopulator` — reads RawDataset + URN metadata, INSERTs into DB |

**Files to modify**:
| File | Change |
|---|---|
| `src/reqstool/model_generators/combined_raw_datasets_generator.py` | Accept `RequirementsDatabase` param. After each `__parse_source()`, call `DatabasePopulator.populate_from_raw_dataset(db, urn, raw_dataset)`. Store parsing_graph edges and urn_metadata in DB. Remove `raw_datasets: Dict` accumulation. |
| `src/reqstool/common/validators/semantic_validator.py` | `validate_post_parsing()` takes `RequirementsDatabase` instead of `CombinedRawDataset`. Rewrite `_requirement_id_exists()` and `_svc_id_exists()` as SQL queries. |
| `src/reqstool/models/raw_datasets.py` | Delete `CombinedRawDataset` class. Keep `RawDataset` as transient per-URN container. |

**Populator logic** (from `CombinedIndexedDatasetGenerator.__process_*` methods):
- `populate_from_raw_dataset(db, urn, rd: RawDataset)`:
  - `INSERT INTO requirements` from `rd.requirements_data.requirements`
  - `INSERT INTO svcs` + `svc_requirement_links` from `rd.svcs_data.cases`
  - `INSERT INTO mvrs` + `mvr_svc_links` from `rd.mvrs_data.results`
  - `INSERT INTO annotations_impls/tests` from `rd.annotations_data`
  - `INSERT INTO test_results` from `rd.automated_tests`
  - Filter definitions from `rd.requirements_data.filters` and `rd.svcs_data.filters` are NOT stored — they are passed directly to the filter processor in Phase 3

**Accessibility pruning** (currently in `CombinedIndexedDatasetGenerator.__process_svcs` lines 154-190):
The populator inserts ALL data. Accessibility-based pruning happens in the filter phase (Phase 3), not during insertion. This simplifies the populator and matches the issue's design: "INSERT all data → DELETE filtered items".

**Tests**:
- `tests/unit/reqstool/storage/test_populator.py` — populate from existing test fixtures, verify row counts
- Update existing `semantic_validator` tests to use DB-backed validation

---

## Phase 3: EL→SQL compiler + SQL-based filter processor

**Goal**: Replace `_IndexedDatasetFilterProcessor` (391 lines) with SQL DELETEs + ON DELETE CASCADE.

**New files**:
| File | Purpose |
|---|---|
| `src/reqstool/storage/el_compiler.py` | Compile Lark AST → SQL WHERE clause + params |
| `src/reqstool/storage/filter_processor.py` | `DatabaseFilterProcessor` — recursive DAG walk, SQL DELETE |

**EL→SQL mapping**:
| Expression | SQL |
|---|---|
| `ids == "REQ_A", "REQ_B"` | `(urn, id) IN (VALUES (?,?), (?,?))` |
| `ids != "REQ_A"` | `NOT ((urn, id) IN (VALUES (?,?)))` |
| `ids == /regex/` | `(urn \|\| ':' \|\| id) REGEXP ?` |
| `and/or/not` | direct SQL equivalents |

Register `REGEXP` via `conn.create_function("REGEXP", 2, ...)`.

**`DatabaseFilterProcessor.apply_filters(db, raw_datasets)`**:
1. Read `parsing_graph` from DB; read filter definitions from transient `RawDataset` objects
2. Recursively walk DAG (same as current `__process_req_filters_per_urn`)
3. For each filter definition, compile EL to SQL WHERE and execute: `DELETE FROM requirements WHERE urn = ? AND id IN (SELECT id FROM requirements WHERE urn = ? AND NOT (<compiled_where>))`
4. `ON DELETE CASCADE` automatically removes linked SVCs → MVRs → annotations → test results
5. Also handles accessibility pruning: DELETE requirements/SVCs from non-accessible URNs

**Key files being replaced**:
- `src/reqstool/model_generators/indexed_dataset_filter_processor.py` (391 lines) — deleted in Phase 5
- `src/reqstool/model_generators/combined_indexed_dataset_generator.py` (303 lines) — the indexing part is now SQL JOINs; filter part replaced here

**Tests**:
- `tests/unit/reqstool/storage/test_el_compiler.py` — compile expressions, verify SQL + params
- `tests/unit/reqstool/storage/test_filter_processor.py` — compare filtering results against existing test fixtures

---

## Phase 4: Migrate commands to query DB directly — eliminate CID and StatisticsContainer

**Goal**: Rewrite all three commands to use `RequirementsDatabase` query methods. Delete `CombinedIndexedDataset`, `StatisticsContainer`, `StatisticsGenerator`.

**Query methods to add to `RequirementsDatabase`**:

```python
# Data queries (replace CID dict lookups)
def get_requirement(self, urn, id) -> RequirementData
def get_all_requirements(self) -> Dict[UrnId, RequirementData]
def get_svcs_for_requirement(self, req_urn, req_id) -> List[SVCData]
def get_mvrs_for_svc(self, svc_urn, svc_id) -> List[MVRData]
def get_annotations_impls_for_req(self, req_urn, req_id) -> List[AnnotationData]
def get_annotations_tests_for_svc(self, svc_urn, svc_id) -> List[AnnotationData]
def get_test_results_for_fqn(self, urn, fqn) -> List[TestData]

# Status statistics (replace StatisticsGenerator._calculate + StatisticsContainer)
def get_requirement_status(self, req_urn, req_id) -> dict  # per-req stats
def get_totals(self) -> dict  # aggregate stats

# Export data (replace CID.model_dump)
def to_export_dict(self) -> dict  # conforms to export_output.schema.json
def to_status_dict(self) -> dict  # conforms to status_output.schema.json

# Metadata
def get_initial_urn(self) -> str
def get_urn_parsing_order(self) -> List[str]
def get_import_graph(self) -> Dict[str, List[str]]
def is_filtered(self) -> bool
```

**Commands rewrite**:

| Command | Current pattern | New pattern |
|---|---|---|
| `StatusCommand` | Creates `StatisticsGenerator` → gets `StatisticsContainer` → renders table/JSON | Creates DB → calls `db.to_status_dict()` for JSON or iterates `db.get_all_requirements()` for table |
| `GenerateJsonCommand` | Creates CID → `cid.model_dump(mode="json")` | Creates DB → `db.to_export_dict()` → `json.dumps()`. `--req-ids`/`--svc-ids` filtering becomes SQL WHERE. |
| `ReportCommand` | Creates CID + StatisticsGenerator → builds aggregated data → Jinja2 | Creates DB → `db.get_all_requirements()` with joined SVCs/annotations/MVRs → Jinja2. Note: currently runs pipeline TWICE (once for CID, once for stats) — with SQLite, single DB serves both. |

**JSON output validation**: Add tests that validate `to_export_dict()` and `to_status_dict()` against the JSON schemas from #315.

**Files to modify**:
| File | Change |
|---|---|
| `src/reqstool/commands/status/status.py` | Use `RequirementsDatabase` directly |
| `src/reqstool/commands/generate_json/generate_json.py` | Use `RequirementsDatabase.to_export_dict()` |
| `src/reqstool/commands/report/report.py` | Use `RequirementsDatabase` for data + stats |
| `src/reqstool/commands/report/criterias/group_by.py` | Query DB for grouping instead of iterating CID |
| `src/reqstool/common/validators/lifecycle_validator.py` | Query DB instead of iterating CID dicts |

**Files to delete**:
| File | Reason |
|---|---|
| `src/reqstool/commands/status/statistics_container.py` | Replaced by DB query results |
| `src/reqstool/commands/status/statistics_generator.py` | Replaced by DB aggregate queries |
| `src/reqstool/models/combined_indexed_dataset.py` | Replaced by DB |

---

## Phase 5: Cleanup — delete old code

**Goal**: Remove all dead code from the migration.

**Files to delete**:
| File | Reason |
|---|---|
| `src/reqstool/model_generators/combined_indexed_dataset_generator.py` | 303 lines → replaced by populator + DB queries |
| `src/reqstool/model_generators/indexed_dataset_filter_processor.py` | 391 lines → replaced by `DatabaseFilterProcessor` |
| `src/reqstool/models/combined_indexed_dataset.py` | Replaced by DB |
| `src/reqstool/commands/status/statistics_container.py` | Replaced by DB query results |
| `src/reqstool/commands/status/statistics_generator.py` | Replaced by DB aggregate queries |

**Files to clean up**:
| File | Change |
|---|---|
| `src/reqstool/common/utils.py` | Remove `flatten_all_reqs()`, `flatten_all_svcs()`, `create_accessible_nodes_dict()`, `append_data_item_to_dict_list_entry()`, `extend_data_sequence_to_dict_list_entry()` |
| `src/reqstool/models/raw_datasets.py` | Only `RawDataset` remains (transient per-URN) |

**Tests to update/delete**: Remove tests for deleted classes. Ensure all remaining 223+ tests pass.

---

## Delivery

All phases ship in a **single PR** on a feature branch (never pollute main). Each phase is a logical commit boundary.

---

## Critical source files

| File | Lines | Role |
|---|---|---|
| `model_generators/combined_raw_datasets_generator.py` | 254 | Parser — modify to write to DB (Phase 2) |
| `model_generators/combined_indexed_dataset_generator.py` | 303 | Indexer — logic moves to populator + queries; delete in Phase 5 |
| `model_generators/indexed_dataset_filter_processor.py` | 391 | Filter — replace with SQL DELETE + CASCADE (Phase 3) |
| `commands/status/statistics_generator.py` | 312 | Stats — replace with SQL aggregates (Phase 4) |
| `commands/generate_json/generate_json.py` | 131 | Export — rewrite to use DB (Phase 4) |
| `commands/report/report.py` | 252 | Report — rewrite to use DB (Phase 4) |
| `common/validators/semantic_validator.py` | 277 | Validation — migrate to query DB (Phase 2) |
| `expression_languages/generic_el.py` | 107 | EL grammar — add SQL compiler backend (Phase 3) |

## Verification (every phase)

```bash
# Phase-specific tests
hatch run dev:pytest tests/unit/reqstool/storage/ -v

# Full unit suite
hatch run dev:pytest --cov=reqstool tests/unit

# Regression smoke test (Phase 4+, per CLAUDE.md)
hatch run python src/reqstool/command.py status local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001
hatch run python src/reqstool/command.py report --format asciidoc local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001
hatch run python src/reqstool/command.py export local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001
# Compare output before/after (strip ANSI: sed 's/\x1b\[[0-9;]*m//g')
```

## Immediate next step

**Start with Phase 1** — create `src/reqstool/storage/` package with schema, database class, authorizer, and tests. Pure additive, independently testable, zero risk to existing code.
