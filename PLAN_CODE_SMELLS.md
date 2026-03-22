# Code Smells — Future Issues

Identified during the Pydantic v2 migration (PR #306). These are **not** related to the migration itself and should be addressed in separate issues/PRs.

---

## High Severity

### ~~Scattered `sys.exit()` in location classes~~ — FIXED in PR #329
- `LocationError` / `ArtifactDownloadError` / `ArtifactExtractionError` added to exception hierarchy
- Location classes now raise exceptions; only `command.py` calls `sys.exit()`

### ~~Mutable singleton `TempDirectoryUtil`~~ — FIXED in PR #330
- Replaced with instance-based `TempDirectoryManager` (context manager, DI, guaranteed cleanup)

---

## Medium Severity

### ~~Duplicated filter parsing logic~~ — FIXED in PR #332
- Extracted `parse_filters()` into `common/filter_parser.py`; both generators reduced to 3-line calls; `# NOSONAR` removed

### ~~Monolithic `status.py` with manual table rendering (322 lines)~~ — FIXED in PR #335
- Replaced `colorama` + `tabulate` with Rich (`Panel`, `Table`, `Text`, `Console`) in `status.py` and `semantic_validator.py`
- Removed `colorama` and `tabulate` dependencies; added `rich>=13.0`
- Reduced from 323 → 255 lines

### ~~No unit tests for CLI entry point~~ — FIXED in PR #331
- Added `tests/unit/reqstool/test_command.py` with 12 tests covering routing, deprecation warnings, error handling, argument parsing

---

## Low Severity

### ~~Repetitive CLI parser setup~~ — FIXED in PR #333
- Replaced 52-line repetitive body of `_add_subparsers_source` with `_LOCATION_DEFS` config dict + 16-line loop

---

## Resolved (no longer valid)

### `@dataclass` in generators/validators — RESOLVED
- `combined_indexed_dataset_generator.py` and `indexed_dataset_filter_processor.py` no longer exist
- Remaining `@dataclass` use in `syntax_validator.py` is legitimate (schema registry item)

### Expression language — empty subclasses — RESOLVED
- `requirements_el.py` and `svcs_el.py` no longer exist; generic transformer used directly
