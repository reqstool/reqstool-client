# Plan: #313 — Replace intermediate data structures with in-memory SQLite

## Context

The current pipeline: `Location → RawDataset → CombinedRawDataset → CombinedIndexedDataset → StatisticsContainer → Commands`

**Goal**: Eliminate `CombinedRawDataset`, `CombinedIndexedDataset`, and `StatisticsContainer` entirely. Replace with in-memory SQLite as single source of truth. Commands query the DB directly — no transitional bridge, no CID materialization.

The parser keeps producing per-URN `RawDataset` (useful for Pydantic validation), but feeds each one into SQLite immediately instead of collecting into `CombinedRawDataset`.

**End state**: `Location → parse → RawDataset (transient) → INSERT into SQLite → commands query DB`

---

## Phase 1: SQLite infrastructure — schema, database class, security ✅

**Status**: Complete (commit 4a3534b + e2430de)

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

---

## Phase 2: Populator + parser integration ✅

**Status**: Complete (commit 4a3534b)

**Goal**: `CombinedRawDatasetsGenerator` takes a `RequirementsDatabase`, inserts each parsed `RawDataset` into it.

**New file**:
| File | Purpose |
|---|---|
| `src/reqstool/storage/populator.py` | `DatabasePopulator` — reads RawDataset + URN metadata, INSERTs into DB |

---

## Phase 3: EL→SQL compiler + SQL-based filter processor ✅

**Status**: Complete (commit b0ef062)

**Goal**: Replace `_IndexedDatasetFilterProcessor` (391 lines) with SQL DELETEs + ON DELETE CASCADE.

**New files**:
| File | Purpose |
|---|---|
| `src/reqstool/storage/el_compiler.py` | Compile Lark AST → SQL WHERE clause + params |
| `src/reqstool/storage/filter_processor.py` | `DatabaseFilterProcessor` — recursive DAG walk, SQL DELETE |

---

## Phase 4: Migrate commands to query DB directly — eliminate CID and StatisticsGenerator

**Status**: In progress. Phases 1–3 completed. Branch `feat/313-sqlite-storage` has 3 commits, 292 tests passing.

**Goal**: Replace the CRD→CID pipeline in all three commands with direct DB queries. Eliminate `CombinedIndexedDataset`, `CombinedIndexedDatasetGenerator`, `StatisticsGenerator`, and `IndexedDatasetFilterProcessor` from the command paths.

**Key design decisions**:
1. **Delete `StatisticsContainer` + `StatisticsGenerator`** entirely — replace with clean `StatisticsService` that returns simple dataclasses. The console presentation code in `status.py` will be updated to use the new data structures.
2. **Java-style Repository + Service layers**:
   - `RequirementsRepository` — data access (query/read methods), wraps `RequirementsDatabase`
   - `StatisticsService` — business logic for computing per-requirement and total statistics
   - `ExportService` — business logic for building export dict conforming to schema
3. **Keep `CombinedRawDataset`** for now — still needed by `semantic_validator.validate_post_parsing()` and `DatabaseFilterProcessor` (reads filters from `raw_datasets`). Full elimination deferred to Phase 5.
4. **JSON output format change** — Both `status --format json` and `export` will produce output conforming to the schemas from #315 (`status_output.schema.json`, `export_output.schema.json`). This is a breaking change from the current `model_dump_json()` format.
5. **Test result resolution at query time** — The CID generator's `__process_automated_test_result` logic (matching test annotations to JUnit results, CLASS aggregation, MISSING detection) moves into a repository query method.
6. **ReportCommand runs pipeline ONCE** instead of twice (currently runs CRD→CID for data AND CRD→CID→StatisticsGenerator for stats separately).

---

### Step 4.1: Pipeline helper — `build_database()`

**New file**: `src/reqstool/storage/pipeline.py`

```python
def build_database(
    location: LocationInterface,
    semantic_validator: SemanticValidator,
    filter_data: bool = True,
) -> Tuple[RequirementsDatabase, CombinedRawDataset]:
    db = RequirementsDatabase()
    crdg = CombinedRawDatasetsGenerator(
        initial_location=location,
        semantic_validator=semantic_validator,
        database=db,
    )
    crd = crdg.combined_raw_datasets
    if filter_data:
        DatabaseFilterProcessor(db, crd.raw_datasets).apply_filters()
    LifecycleValidator(db)  # after migration in step 4.5
    return db, crd
```

All three commands will call `build_database()` instead of manually creating CRD→CID.

---

### Step 4.2: `RequirementsRepository` — data access layer

**New file**: `src/reqstool/storage/requirements_repository.py`

Wraps `RequirementsDatabase` and provides all read/query methods. Reconstructs domain objects from DB rows.

```python
class RequirementsRepository:
    def __init__(self, db: RequirementsDatabase):
        self._db = db
```

**Private helpers** (reconstruct domain objects from DB rows):
- `_row_to_requirement_data(row)` → joins `requirement_categories` + `requirement_references`, reconstructs `RequirementData` with `LifecycleData`, `IMPLEMENTATION`, `CATEGORIES`, `SIGNIFICANCETYPES`, `ReferenceData`, version parsing
- `_row_to_svc_data(row)` → joins `svc_requirement_links`, reconstructs `SVCData`
- `_row_to_mvr_data(row)` → joins `mvr_svc_links`, reconstructs `MVRData`

**Metadata queries**:
```python
def get_initial_urn(self) -> str
def get_urn_parsing_order(self) -> List[str]  # SELECT urn FROM urn_metadata ORDER BY parse_position
def get_import_graph(self) -> Dict[str, List[str]]  # SELECT from parsing_graph
def is_filtered(self) -> bool  # get_metadata("filtered") == "true"
```

**Entity queries** (return domain objects, not raw rows):
```python
def get_all_requirements(self) -> Dict[UrnId, RequirementData]
def get_all_svcs(self) -> Dict[UrnId, SVCData]
def get_all_mvrs(self) -> Dict[UrnId, MVRData]
```

**Index/lookup queries** (replace CID cross-reference indexes):
```python
def get_svcs_for_req(self, req_urn_id: UrnId) -> List[UrnId]
    # SELECT svc_urn, svc_id FROM svc_requirement_links WHERE req_urn=? AND req_id=?
def get_mvrs_for_svc(self, svc_urn_id: UrnId) -> List[UrnId]
    # SELECT mvr_urn, mvr_id FROM mvr_svc_links WHERE svc_urn=? AND svc_id=?
def get_annotations_impls(self) -> Dict[UrnId, List[AnnotationData]]
def get_annotations_tests(self) -> Dict[UrnId, List[AnnotationData]]
def get_annotations_impls_for_req(self, req_urn_id: UrnId) -> List[AnnotationData]
def get_annotations_tests_for_svc(self, svc_urn_id: UrnId) -> List[AnnotationData]
```

**Test result resolution** (replaces `CombinedIndexedDatasetGenerator.__process_automated_test_result`):
```python
def get_automated_test_results(self) -> Dict[UrnId, List[TestData]]
    # For each annotation in annotations_tests:
    #   key = UrnId(urn=svc_urn, id=fqn)
    #   If element_kind == "CLASS":
    #     Find all test_results WHERE fqn LIKE annotation.fqn || '.%'
    #     Aggregate: all passed → PASSED, any not passed → FAILED, none found → MISSING
    #   Else (METHOD):
    #     Find test_results WHERE fqn = annotation.fqn
    #     If found → use actual status, else → MISSING
```

**Tests**: `tests/unit/reqstool/storage/test_requirements_repository.py` — round-trip: insert → query → verify domain objects match

---

### Step 4.3: `ExportService` — business logic for export

**New file**: `src/reqstool/services/export_service.py`

```python
class ExportService:
    def __init__(self, repository: RequirementsRepository):
        self._repo = repository

    def to_export_dict(self, req_ids=None, svc_ids=None) -> dict:
        ...
```

Produces dict conforming to `export_output.schema.json`:
```python
{
    "metadata": {
        "initial_urn": str,
        "urn_parsing_order": List[str],
        "import_graph": Dict[str, List[str]],
        "filtered": bool,
    },
    "requirements": {"urn:id": {urn, id, title, significance, description, rationale,
                                lifecycle: {state, reason}, implementation_type,
                                categories: [...], revision: {major, minor, patch},
                                references: [{requirement_ids: ["urn:id"]}]}},
    "svcs": {"urn:id": {urn, id, title, description, verification, instructions,
                        lifecycle, revision, requirement_ids: ["urn:id"]}},
    "mvrs": {"urn:id": {urn, id, passed, comment, svc_ids: ["urn:id"]}},
    "annotations": {
        "implementations": {"urn:req_id": [{element_kind, fully_qualified_name}]},
        "tests": {"urn:svc_id": [{element_kind, fully_qualified_name}]},
    },
    "test_results": {"urn:fqn": [{fully_qualified_name, status}]},
}
```

**`--req-ids`/`--svc-ids` filtering**: When provided, filter requirements/SVCs/MVRs via repository queries. Also include related entities (SVCs for kept reqs, MVRs for kept SVCs, reqs for kept SVCs if only `--svc-ids` specified).

**Tests**: `tests/unit/reqstool/services/test_export_service.py` — validate output against `export_output.schema.json` with `jsonschema.validate()`.

---

### Step 4.4: `StatisticsService` — replaces StatisticsGenerator + StatisticsContainer

**New file**: `src/reqstool/services/__init__.py`
**New file**: `src/reqstool/services/statistics_service.py`

**New data structures** (simple frozen dataclasses, replace `TestStatisticsItem`, `CombinedRequirementTestItem`, `TotalStatisticsItem`, `StatisticsContainer`):

```python
@dataclass(frozen=True)
class TestStats:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    missing: int = 0
    not_applicable: bool = False

    def is_completed(self) -> bool:
        if self.missing > 0:
            return False
        return self.total == self.passed

@dataclass(frozen=True)
class RequirementStatus:
    completed: bool = False
    implementations: int = 0
    implementation_type: IMPLEMENTATION = IMPLEMENTATION.IN_CODE
    automated_tests: TestStats = field(default_factory=TestStats)
    manual_tests: TestStats = field(default_factory=TestStats)

@dataclass
class TotalStats:
    total_requirements: int = 0
    completed_requirements: int = 0
    with_implementation: int = 0
    without_implementation_total: int = 0
    without_implementation_completed: int = 0
    total_svcs: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    missing_automated_tests: int = 0
    missing_manual_tests: int = 0
    total_manual_tests: int = 0
    total_annotated_tests: int = 0
    passed_manual_tests: int = 0
    failed_manual_tests: int = 0
    passed_automatic_tests: int = 0
    failed_automatic_tests: int = 0
```

**Service class**:
```python
class StatisticsService:
    def __init__(self, repository: RequirementsRepository):
        self._repo = repository
        self._requirement_stats: Dict[UrnId, RequirementStatus] = {}
        self._totals: TotalStats = TotalStats()
        self._calculate()

    @property
    def requirement_statistics(self) -> Dict[UrnId, RequirementStatus]:
        ...

    @property
    def total_statistics(self) -> TotalStats:
        ...

    def to_status_dict(self) -> dict:
        # Produces dict conforming to status_output.schema.json
        ...
```

Replicates `StatisticsGenerator` logic using repository queries:
- Per requirement: `repo.get_svcs_for_req()` for SVCs, check `verification_type` for expects_mvrs/expects_automated, `repo.get_annotations_impls_for_req()` for impls count, compute MVR/test stats, determine completion
- Totals: aggregate counts from repository

**Console rendering** (`_status_table`, `_build_table`, `_extend_row`, `_summarize_statistics` in `status.py`): Update to use `TestStats`, `RequirementStatus`, `TotalStats` attribute names instead of `TestStatisticsItem`, `CombinedRequirementTestItem`, `TotalStatisticsItem`.

**Tests**: `tests/unit/reqstool/services/test_statistics_service.py` — validate against `status_output.schema.json`, compare stats against existing test fixtures.

---

### Step 4.5: Migrate `LifecycleValidator`

**File**: `src/reqstool/common/validators/lifecycle_validator.py`

Change constructor: `__init__(self, db: RequirementsDatabase)` instead of `__init__(self, cid: CombinedIndexedDataset)`

Rewrite validation methods to use DB queries:
- `_check_defunct_annotations`: Query `annotations_impls` JOIN `requirements` WHERE `lifecycle_state IN ('deprecated', 'obsolete')`, and `annotations_tests` JOIN `svcs`
- `_check_mvr_references`: Query `mvr_svc_links` JOIN `svcs` WHERE `lifecycle_state IN ('deprecated', 'obsolete')`
- `_check_svc_references`: Query `svc_requirement_links` JOIN `requirements` WHERE deprecated/obsolete, filter SVCs that are still active

**Tests**: Update `tests/unit/reqstool/common/validators/test_lifecycle_validator.py` — change fixture to build DB instead of CID.

---

### Step 4.6: Rewrite `StatusCommand`

**File**: `src/reqstool/commands/status/status.py`

```python
def __status_result(self) -> Tuple[str, int]:
    db, _ = build_database(
        location=self.__initial_location,
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    )
    repo = RequirementsRepository(db)
    stats_service = StatisticsService(repo)

    if self.__format == "json":
        status = json.dumps(stats_service.to_status_dict(), indent=2)
    else:
        status = _status_table(stats_service)

    db.close()
    return (status, stats_service.total_statistics.total_requirements
            - stats_service.total_statistics.completed_requirements)
```

- Remove imports: `StatisticsGenerator`, `StatisticsContainer`, `TestStatisticsItem`
- Add imports: `build_database`, `RequirementsRepository`, `StatisticsService`, `TestStats`, `RequirementStatus`, `TotalStats`
- **Console rendering updates**: `_status_table`, `_build_table`, `_extend_row`, `_get_row_with_totals`, `_summarize_statistics` — update attribute names:
  - `stats.nr_of_implementations` → `stats.implementations`
  - `stats.automated_tests_stats` → `stats.automated_tests`
  - `stats.mvrs_stats` → `stats.manual_tests`
  - `result.nr_of_total_tests` → `result.total`
  - `result.nr_of_passed_tests` → `result.passed`
  - `result.nr_of_failed_tests` → `result.failed`
  - `result.nr_of_skipped_tests` → `result.skipped`
  - `result.nr_of_missing_automated_tests` → `result.missing` (for automated)
  - `result.nr_of_missing_manual_tests` → `result.missing` (for manual)
  - `ts.nr_of_total_requirements` → `ts.total_requirements`
  - etc.
- **JSON output changes** to conform to `status_output.schema.json`

**Tests**: Update `tests/unit/reqstool/commands/status/test_status.py` and `test_status_presentation.py` — adjust attribute names in assertions.

---

### Step 4.7: Rewrite `GenerateJsonCommand`

**File**: `src/reqstool/commands/generate_json/generate_json.py`

```python
def __run(self) -> str:
    holder = ValidationErrorHolder()
    db, _ = build_database(
        location=self.__initial_location,
        semantic_validator=SemanticValidator(validation_error_holder=holder),
        filter_data=self.__filter_data,
    )
    repo = RequirementsRepository(db)
    export_service = ExportService(repo)
    export_dict = export_service.to_export_dict(req_ids=self.__req_ids, svc_ids=self.__svc_ids)
    db.close()
    return json.dumps(export_dict, separators=(", ", ": "))
```

- Delete `_filter_by_ids()`, `_resolve_ids()`, `_filter_index()`, `_collect_related()` — filtering now in `ExportService`
- Remove imports: `CombinedIndexedDatasetGenerator`, `CombinedRawDatasetsGenerator`, `CombinedIndexedDataset`, `CombinedRawDataset`
- Add imports: `build_database`, `RequirementsRepository`, `ExportService`
- **JSON output changes** to conform to `export_output.schema.json`

**Tests**: Update `tests/unit/reqstool/commands/generate_json/test_generate_json.py` — tests check for keys like `"ms-001:REQ_010" in result["requirements"]` which still works with the new schema. Adjust any tests that check the value structure.

---

### Step 4.8: Rewrite `ReportCommand`

**File**: `src/reqstool/commands/report/report.py`

```python
def __run(self) -> str:
    db, _ = build_database(
        location=self.__initial_location,
        semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
    )
    repo = RequirementsRepository(db)
    aggregated_data = self.__aggregated_requirements_data(repo=repo)
    stats_service = StatisticsService(repo)
    report = self.__generate_report(repo=repo, aggregated_data=aggregated_data, statistics=stats_service)
    db.close()
    return report
```

Key changes:
- **Single pipeline** instead of two (CID + StatisticsGenerator run separately)
- `__aggregated_requirements_data(repo)` — queries repository instead of iterating CID dicts:
  - `repo.get_all_requirements()` for requirements
  - `repo.get_svcs_for_req()` for related SVCs per requirement
  - `repo.get_annotations_impls_for_req()` for implementations
  - `repo.get_mvrs_for_svc()` for MVRs (via SVCs)
  - `repo.get_annotations_tests_for_svc()` for test annotations
  - `repo.get_automated_test_results()` for test results
- `__generate_report` and `__extract_template_data` stay largely unchanged (they work with dicts, not CID)
- `GroupByOrganizor` needs migration (step 4.9)
- Remove `Utils.get_mvr_urn_ids_for_svcs_urn_id` usage — replace with `repo.get_mvrs_for_svc()`
- Remove imports: `CombinedIndexedDatasetGenerator`, `CombinedRawDatasetsGenerator`, `CombinedIndexedDataset`, `StatisticsGenerator`, `StatisticsContainer`, `Utils`
- Add imports: `build_database`, `RequirementsRepository`, `StatisticsService`

**Tests**: Update `tests/unit/reqstool/commands/report/test_report.py` — should require minimal changes since tests verify rendered output content.

---

### Step 4.9: Migrate `GroupByOrganizor`

**File**: `src/reqstool/commands/report/criterias/group_by.py`

Change field: `cid: CombinedIndexedDataset` → `repo: RequirementsRepository`

```python
class GroupByOrganizor(BaseModel, ABC):
    repo: RequirementsRepository
    # ... rest unchanged

    def _group(self):
        for urn_id, req_data in self.repo.get_all_requirements().items():
            group = group_by_functions[self.group_by](req_data=req_data, repo=self.repo)
            self._add_req_to_group(group=group, urn_id=urn_id)

    def _sort(self):
        requirements = self.repo.get_all_requirements()
        for group, urn_ids in self.grouped_requirements.items():
            urn_ids.sort(
                key=lambda uid: attrgetter(*[so.value for so in self.sort_by])(requirements[uid])
            )
```

Update lambda functions:
```python
group_by_category = lambda req_data, repo: (
    req_data.categories[0].value if req_data.categories else "No Category"
)
group_by_initial_imported = lambda req_data, repo: (
    f"Initial URN ({repo.get_initial_urn()})" if req_data.id.urn == repo.get_initial_urn() else "Imported"
)
```

**Tests**: Update `tests/unit/reqstool/commands/report/criterias/test_criterias.py` — change fixture to build DB + repo.

---

### Step 4.10: Update all affected tests

**13 test files** need updates. Grouped by change type:

**A. Tests that create CRD→CID pipeline (change to DB pipeline)**:
| File | Change |
|---|---|
| `tests/unit/reqstool/commands/status/test_statistics_generator.py` | Replace with `tests/unit/reqstool/services/test_statistics_service.py` (new) |
| `tests/unit/reqstool/commands/status/test_statistics_generator_methods.py` | Replace with tests in `test_statistics_service.py` |
| `tests/unit/reqstool/commands/status/test_status.py` | Should work as-is (tests `StatusCommand` which we're rewriting) |
| `tests/unit/reqstool/commands/generate_json/test_generate_json.py` | Should work as-is (tests `GenerateJsonCommand`). Adjust value assertions for new export schema format. |
| `tests/unit/reqstool/commands/report/test_report.py` | Should work as-is (tests `ReportCommand` which we're rewriting) |
| `tests/unit/reqstool/commands/report/criterias/test_criterias.py` | Change to build DB + repo instead of CID |
| `tests/unit/reqstool/common/validators/test_lifecycle_validator.py` | Change fixture to build DB + repo |

**B. Tests that import CID/CRD but test filtering (should NOT change — filtering tests are in storage/)**:
| File | Notes |
|---|---|
| `tests/unit/reqstool/filters/test_requirements_filters.py` | Still tests old pipeline. Will be updated when old pipeline is deleted in Phase 5. |
| `tests/unit/reqstool/filters/test_software_verification_cases_filters.py` | Same as above. |

**C. Tests with attribute name changes**:
| File | Notes |
|---|---|
| `tests/unit/reqstool/commands/status/test_status_presentation.py` | Update attribute names for `TestStats` / `TotalStats` (e.g. `nr_of_total_tests` → `total`) |

**D. Tests unchanged**:
| File | Notes |
|---|---|
| `tests/unit/reqstool/model_generators/test_combined_raw_datasets_generator.py` | Tests CRD generator — unaffected |
| `tests/unit/reqstool/model_generators/test_combined_indexed_dataset_generator.py` | Tests old CID generator — left for Phase 5 deletion |

**E. Tests deleted in Phase 4** (no longer applicable):
| File | Notes |
|---|---|
| `tests/unit/reqstool/commands/status/test_statistics_container.py` | Model deleted — new data structures tested in `test_statistics_service.py` |

---

### Files summary

**New files**:
| File | Purpose |
|---|---|
| `src/reqstool/storage/pipeline.py` | `build_database()` helper |
| `src/reqstool/storage/requirements_repository.py` | `RequirementsRepository` — data access layer |
| `src/reqstool/services/__init__.py` | Services package init |
| `src/reqstool/services/statistics_service.py` | `StatisticsService` + `TestStats`/`RequirementStatus`/`TotalStats` dataclasses |
| `src/reqstool/services/export_service.py` | `ExportService` — builds export dict |
| `tests/unit/reqstool/storage/test_requirements_repository.py` | Repository query tests |
| `tests/unit/reqstool/services/__init__.py` | Test package init |
| `tests/unit/reqstool/services/test_statistics_service.py` | Statistics calculation tests |
| `tests/unit/reqstool/services/test_export_service.py` | Export output tests |

**Files to modify**:
| File | Change |
|---|---|
| `src/reqstool/commands/status/status.py` | Use `RequirementsRepository` + `StatisticsService`, update presentation attribute names |
| `src/reqstool/commands/generate_json/generate_json.py` | Use `RequirementsRepository` + `ExportService`, delete 4 static methods |
| `src/reqstool/commands/report/report.py` | Use `RequirementsRepository` + `StatisticsService`, single pipeline |
| `src/reqstool/commands/report/criterias/group_by.py` | Accept `RequirementsRepository` instead of CID |
| `src/reqstool/common/validators/lifecycle_validator.py` | Accept `RequirementsDatabase` instead of CID |
| 7 test files | (see step 4.10) |

**Files NOT deleted in Phase 4** (deferred to Phase 5):
- `statistics_container.py` — no longer imported by commands, kept until Phase 5
- `statistics_generator.py` — no longer imported by commands, kept until Phase 5
- `combined_indexed_dataset.py` — no longer imported by commands, kept until Phase 5
- `combined_indexed_dataset_generator.py` — kept until Phase 5
- `indexed_dataset_filter_processor.py` — kept until Phase 5

---

## Phase 5: Cleanup — delete old code

**Goal**: Remove all dead code from the migration.

**Files to delete**:
| File | Reason |
|---|---|
| `src/reqstool/model_generators/combined_indexed_dataset_generator.py` | 303 lines — replaced by populator + repository |
| `src/reqstool/model_generators/indexed_dataset_filter_processor.py` | 391 lines — replaced by `DatabaseFilterProcessor` |
| `src/reqstool/models/combined_indexed_dataset.py` | Replaced by DB + repository |
| `src/reqstool/commands/status/statistics_generator.py` | Replaced by `StatisticsService` |
| `src/reqstool/commands/status/statistics_container.py` | Replaced by `TestStats`/`RequirementStatus`/`TotalStats` in `StatisticsService` |

**Files to clean up**:
| File | Change |
|---|---|
| `src/reqstool/common/utils.py` | Remove `flatten_all_reqs()`, `flatten_all_svcs()`, `create_accessible_nodes_dict()`, `append_data_item_to_dict_list_entry()`, `extend_data_sequence_to_dict_list_entry()`, `get_mvr_urn_ids_for_svcs_urn_id()` |
| `src/reqstool/models/raw_datasets.py` | Delete `CombinedRawDataset` if semantic_validator is also migrated to use DB |

**Tests to update/delete**:
| File | Action |
|---|---|
| `tests/unit/reqstool/model_generators/test_combined_indexed_dataset_generator.py` | Delete |
| `tests/unit/reqstool/commands/status/test_statistics_generator.py` | Delete (replaced by test_statistics_service.py) |
| `tests/unit/reqstool/commands/status/test_statistics_generator_methods.py` | Delete (replaced by test_statistics_service.py) |
| `tests/unit/reqstool/commands/status/test_statistics_container.py` | Delete (replaced by test_statistics_service.py) |
| `tests/unit/reqstool/filters/test_requirements_filters.py` | Rewrite to use DB pipeline |
| `tests/unit/reqstool/filters/test_software_verification_cases_filters.py` | Rewrite to use DB pipeline |

---

## Verification (Phase 4)

```bash
# Phase-specific tests
hatch run dev:pytest tests/unit/reqstool/storage/ -v

# Full unit suite
hatch run dev:pytest --cov=reqstool tests/unit

# Regression smoke test — console output must be IDENTICAL
hatch run python src/reqstool/command.py status local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
hatch run python src/reqstool/command.py status local -p tests/resources/test_data/data/local/test_basic/baseline/ms-101 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
hatch run python src/reqstool/command.py report --format asciidoc local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001
hatch run python src/reqstool/command.py report --format asciidoc local -p tests/resources/test_data/data/local/test_basic/baseline/ms-101
hatch run python src/reqstool/command.py export local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001

# JSON output validation against schemas
hatch run python src/reqstool/command.py status --format json local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001 | python -c "import sys,json,jsonschema; schema=json.load(open('src/reqstool/resources/schemas/v1/status_output.schema.json')); jsonschema.validate(json.load(sys.stdin), schema); print('OK')"
hatch run python src/reqstool/command.py export local -p tests/resources/test_data/data/local/test_standard/baseline/ms-001 | python -c "import sys,json,jsonschema; schema=json.load(open('src/reqstool/resources/schemas/v1/export_output.schema.json')); jsonschema.validate(json.load(sys.stdin), schema); print('OK')"
```

## Implementation order (Phase 4)

1. Step 4.2: `RequirementsRepository` (data access layer) + tests
2. Step 4.1: `build_database()` pipeline helper
3. Step 4.4: `StatisticsService` + data structures + tests
4. Step 4.3: `ExportService` + tests
5. Step 4.5: Migrate `LifecycleValidator`
6. Step 4.6–4.9: Rewrite commands + GroupByOrganizor
7. Step 4.10: Update remaining tests
8. Regression smoke tests
