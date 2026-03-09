# Code Smells — Future Issues

Identified during the Pydantic v2 migration (PR #306). These are **not** related to the migration itself and should be addressed in separate issues/PRs.

---

## High Severity

### Scattered `sys.exit()` in location classes
- **Files:** `maven_location.py:42-53`, `pypi_location.py:39-58`, `command.py:379-402`
- **Problem:** Location classes call `sys.exit(1)` directly instead of raising exceptions. Makes unit testing impossible without mocking `sys.exit()`. Inconsistent error context (`RuntimeError` vs `RequestException`).
- **Fix:** Create exception hierarchy (`LocationException`, `ArtifactNotFoundError`, etc.). Only `command.py` should call `sys.exit()`.

### Mutable singleton `TempDirectoryUtil`
- **Files:** `common/utils.py:346-372`
- **Problem:** Mutable class-level state (`tmpdir`, `count`), lazy init singleton, no cleanup guarantee, thread-unsafe counter. Test pollution risk.
- **Fix:** Replace with dependency-injected `TempDirectoryManager` using context managers for guaranteed cleanup.

---

## Medium Severity

### Duplicated filter parsing logic
- **Files:** `requirements_model_generator.py:250-299`, `svcs_model_generator.py:72-115`
- **Problem:** Two near-identical ~50-line methods parse filters with same dict keys, same nesting, same UrnId conversion. Both have `# NOSONAR` suppression.
- **Fix:** Extract into a shared `FilterParser` utility. Both methods reduce to 3-line calls.

### Monolithic `status.py` with manual table rendering (428 lines)
- **Files:** `commands/status/status.py:78-200+`
- **Problem:** Mixes statistics calculation, manual Unicode box-drawing, and ANSI color handling. 70-line function just for merged headers. Works around `tabulate` library limitations.
- **Fix:** Replace manual table rendering with **Rich** library. Eliminates ~300 lines of string manipulation.

### No unit tests for CLI entry point
- **Files:** `src/reqstool/command.py` (408 lines)
- **Problem:** Main CLI entry point has zero unit tests. Only legacy E2E test exists for deprecated `generate-json`. Contains a `TODO $$$` comment.
- **Fix:** Add `tests/unit/reqstool/test_command.py` covering argument parsing, location routing, error handling, deprecation warnings.

---

### Remaining `@dataclass` in generators/validators
- **Files:** `combined_indexed_dataset_generator.py`, `indexed_dataset_filter_processor.py`, `syntax_validator.py`
- **Problem:** Three infrastructure/service classes still use `@dataclass` after the Pydantic migration, creating inconsistency. They have 100+ internal `_` prefixed field references that Pydantic treats as `PrivateAttr`, so converting requires renaming all fields.
- **Fix:** Convert to `BaseModel`, rename `_` prefixed fields to public names. Large diff but purely cosmetic — these are behavioral classes, not data models.

---

## Low Severity

### Repetitive CLI parser setup
- **Files:** `command.py:115-169`
- **Problem:** Four location types repeat ~8 lines each of parser registration. Deprecated wrappers (`report-asciidoc`, `generate-json`) still exist as code.
- **Fix:** Config-driven builder pattern with a location registry dict.

### Expression language — minor inefficiencies
- **Files:** `expression_languages/generic_el.py`, `requirements_el.py`, `svcs_el.py`
- **Assessment:** Lark is the right tool — 26-line grammar, LALR parser, handles operator precedence and regex. **Not over-engineered.**
- **Minor issues:**
  1. `RequirementsELTransformer` and `SVCsELTransformer` are empty `pass` subclasses — no runtime value
  2. New transformer instance created per item evaluated — could cache and reuse
  3. Regex and nested boolean logic exist in grammar but production YAML only uses simple expressions
- **Fix:** Remove empty subclasses, optimize transformer reuse. Low effort.
