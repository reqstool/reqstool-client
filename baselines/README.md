# Regression Baselines

This directory contains CLI output captured from `main` **before** the Pydantic v2 migration.
Use these baselines to verify that code changes don't produce unintended output differences.

**This directory should be removed before merging to `main`.**

## How baselines were captured

All baselines were captured on `main` at commit `784f77b` (the first commit on the feature branch).

### Naming convention

```
<dataset>__<command>.txt       — CLI stdout (+ stderr for status)
<dataset>__<command>.exitcode  — exit code of the command
```

### Datasets

| Baseline prefix | Fixture path |
|---|---|
| `test_standard_baseline_ms-001` | `tests/resources/test_data/data/local/test_standard/baseline/ms-001` |
| `test_standard_baseline_sys-001` | `tests/resources/test_data/data/local/test_standard/baseline/sys-001` |
| `test_standard_empty_ms_ms-001` | `tests/resources/test_data/data/local/test_standard/empty_ms/ms-001` |
| `test_standard_empty_ms_sys-001` | `tests/resources/test_data/data/local/test_standard/empty_ms/sys-001` |
| `test_basic_baseline_ms-101` | `tests/resources/test_data/data/local/test_basic/baseline/ms-101` |
| `test_basic_lifecycle_ms-101` | `tests/resources/test_data/data/local/test_basic/lifecycle/ms-101` |
| `test_basic_lifecycle_validation_error` | `tests/resources/test_data/data/local/test_basic/lifecycle/validation_error` |
| `test_basic_no_impls_basic_ms-101` | `tests/resources/test_data/data/local/test_basic/no_impls/basic/ms-101` |
| `test_basic_no_impls_with_error_ms-101` | `tests/resources/test_data/data/local/test_basic/no_impls/with_error/ms-101` |
| `test_delete_mvr_ms-001` | `tests/resources/test_data/data/local/test_delete_mvr/ms-001` |
| `test_delete_mvr_sys-001` | `tests/resources/test_data/data/local/test_delete_mvr/sys-001` |
| `test_errors_ms-101` | `tests/resources/test_data/data/local/test_errors/ms-101` |
| `reqstool_demo` | `../reqstool-demo/docs/reqstool` (sibling project, requires `./mvnw verify` first) |

## Running regression tests

### 1. Run pytest

```bash
hatch run dev:pytest --override-ini="log_cli=false" -q
```

### 2. Compare CLI output against baselines

For each in-repo dataset, run all 4 commands and diff against the baseline:

```bash
# Status (strip ANSI color codes)
hatch run dev:python src/reqstool/command.py status local -p <FIXTURE_PATH> 2>&1 \
  | sed 's/\x1b\[[0-9;]*m//g' > /tmp/feature-status.txt
diff baselines/<DATASET>__status.txt /tmp/feature-status.txt

# Report (AsciiDoc)
hatch run dev:python src/reqstool/command.py report --format asciidoc local -p <FIXTURE_PATH> \
  > /tmp/feature-report-adoc.txt 2>&1
diff baselines/<DATASET>__report_adoc.txt /tmp/feature-report-adoc.txt

# Report (Markdown)
hatch run dev:python src/reqstool/command.py report --format markdown local -p <FIXTURE_PATH> \
  > /tmp/feature-report-md.txt 2>&1
diff baselines/<DATASET>__report_md.txt /tmp/feature-report-md.txt

# Export (JSON)
hatch run dev:python src/reqstool/command.py export local -p <FIXTURE_PATH> \
  > /tmp/feature-export.txt 2>&1
diff baselines/<DATASET>__export.txt /tmp/feature-export.txt
```

### 3. Quick full regression script

Run all in-repo datasets at once (copy-paste friendly):

```bash
cd /path/to/reqstool-client

# Key datasets to check
for ds in \
  "test_standard_baseline_ms-001 tests/resources/test_data/data/local/test_standard/baseline/ms-001" \
  "test_standard_baseline_sys-001 tests/resources/test_data/data/local/test_standard/baseline/sys-001" \
  "test_basic_baseline_ms-101 tests/resources/test_data/data/local/test_basic/baseline/ms-101"; do

  name=$(echo $ds | cut -d' ' -f1)
  path=$(echo $ds | cut -d' ' -f2)

  echo "=== $name ==="

  hatch run dev:python src/reqstool/command.py status local -p $path 2>&1 \
    | sed 's/\x1b\[[0-9;]*m//g' > /tmp/f.txt
  diff -q baselines/${name}__status.txt /tmp/f.txt && echo "  status: OK" || echo "  status: DIFF"

  hatch run dev:python src/reqstool/command.py report --format asciidoc local -p $path > /tmp/f.txt 2>&1
  diff -q baselines/${name}__report_adoc.txt /tmp/f.txt && echo "  report_adoc: OK" || echo "  report_adoc: DIFF"

  hatch run dev:python src/reqstool/command.py report --format markdown local -p $path > /tmp/f.txt 2>&1
  diff -q baselines/${name}__report_md.txt /tmp/f.txt && echo "  report_md: OK" || echo "  report_md: DIFF"

  hatch run dev:python src/reqstool/command.py export local -p $path > /tmp/f.txt 2>&1
  diff -q baselines/${name}__export.txt /tmp/f.txt && echo "  export: OK" || echo "  export: DIFF"
done
```

### 4. reqstool-demo regression

Requires the sibling `../reqstool-demo` project with Maven artifacts built (`./mvnw verify`):

```bash
hatch run dev:python src/reqstool/command.py status local -p ../reqstool-demo/docs/reqstool 2>&1 \
  | sed 's/\x1b\[[0-9;]*m//g' > /tmp/f.txt
diff baselines/reqstool_demo__status.txt /tmp/f.txt

hatch run dev:python src/reqstool/command.py report --format asciidoc local -p ../reqstool-demo/docs/reqstool \
  > /tmp/f.txt 2>&1
diff baselines/reqstool_demo__report_adoc.txt /tmp/f.txt

hatch run dev:python src/reqstool/command.py report --format markdown local -p ../reqstool-demo/docs/reqstool \
  > /tmp/f.txt 2>&1
diff baselines/reqstool_demo__report_md.txt /tmp/f.txt

hatch run dev:python src/reqstool/command.py export local -p ../reqstool-demo/docs/reqstool \
  > /tmp/f.txt 2>&1
diff baselines/reqstool_demo__export.txt /tmp/f.txt
```

## Known expected diffs from Pydantic v2 migration

1. **Export JSON — enum serialization**: Enums now serialize as clean values (`"effective"`)
   instead of verbose jsonpickle format (`{"_value_": "effective", "_name_": "EFFECTIVE", ...}`).
   This affects all datasets' `__export.txt` files.

2. **Standard dataset — implementation counts**: The annotations nesting bug fix
   (`List[List[AnnotationData]]` → `List[AnnotationData]`) changes implementation counts
   in `test_standard_*` status and report outputs where requirements have multiple annotations.
   Basic datasets are unaffected (1 annotation per requirement).

If a diff is expected due to an intentional change, note it in the PR description.
