# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Reqstool** is a CLI tool for managing software requirements, linking them to implementation annotations, software verification cases (SVCs), manual verification results (MVRs), and automated test results (JUnit XML). It generates AsciiDoc reports, JSON exports, and requirement status checks for use in CI/CD pipelines.

Package entry point: `reqstool.command:main` → `src/reqstool/command.py`

## Commands

```bash
# Install in dev mode (hatch manages virtualenvs)
pip install hatch
hatch env create dev

# Run all tests (unit only, integration excluded by default)
hatch run dev:pytest --cov=reqstool

# Run unit tests only
hatch run dev:pytest --cov=reqstool tests/unit

# Run integration tests only
hatch run dev:pytest --cov=reqstool tests/integration

# Run a single test file
hatch run dev:pytest tests/unit/reqstool/model_generators/test_combined_indexed_dataset_generator.py

# Run a single test by name
hatch run dev:pytest -k "test_name"

# Format (black, line-length 120)
hatch run dev:black src tests

# Lint (flake8, max-line-length 125)
hatch run dev:flake8
```

pytest markers: `slow`, `integration`, `flaky`. By default `-m "not slow and not integration"` is applied.

## Architecture

The pipeline flows: **Location** → **RawDataset** → **CombinedRawDataset** → **CombinedIndexedDataset** → **Command output**.

### Locations (`locations/`)
Abstractions for where source data lives. Implementations: `LocalLocation`, `GitLocation`, `MavenLocation`, `PypiLocation`. Each implements `_make_available_on_localdisk(dst_path)` to download/copy the source to a temp dir. `LocationResolver` (`location_resolver/`) handles relative path resolution when an import's location is relative to its parent.

### Data Ingestion (`model_generators/`, `requirements_indata/`)
`CombinedRawDatasetsGenerator` is the top-level parser. It:
1. Resolves the initial location to a local temp path (`TempDirectoryUtil`)
2. Parses `requirements.yml` → `RequirementsModelGenerator` → `RequirementsData`
3. Recursively follows `imports` (other system URNs) and `implementations` (microservice URNs)
4. For each SYSTEM/MICROSERVICE source also parses: `svcs.yml`, `mvrs.yml`, `annotations.yml`, JUnit XML test results
5. Builds a `CombinedRawDataset` (dict keyed by URN string) plus a DAG (`parsing_graph`)

### Core Data Model (`models/`)
All domain objects are frozen/plain `@dataclass`s:
- `UrnId` — composite key `urn:id` (frozen dataclass, hashable)
- `RequirementsData` / `RequirementData` — loaded from `requirements.yml`
- `SVCsData` / `SVCData` — software verification cases from `svcs.yml`
- `MVRsData` / `MVRData` — manual verification results from `mvrs.yml`
- `AnnotationsData` / `AnnotationData` — from `annotations.yml` (code annotations exported by `reqstool-python-decorators`)
- `TestsData` / `TestData` — JUnit XML test results
- `CombinedRawDataset` — flat dict of all raw datasets + parsing graph
- `CombinedIndexedDataset` — fully resolved, indexed, post-filtered dataset used by commands

Variants (defined in `requirements.yml` metadata): `SYSTEM`, `MICROSERVICE`, `EXTERNAL`.

### Indexing & Filtering (`model_generators/combined_indexed_dataset_generator.py`)
`CombinedIndexedDatasetGenerator` takes a `CombinedRawDataset` and produces a `CombinedIndexedDataset` with cross-reference indexes (e.g. `svcs_from_req`, `mvrs_from_svc`). If `_filtered=True`, it applies requirement and SVC filters defined in the YAML using the expression language.

### Expression Language (`expression_languages/`)
Custom Lark-based DSL for filter expressions in `requirements.yml` / `svcs.yml`. Grammar supports `and`, `or`, `not`, `ids ==`, `ids !=`, and regex matching. `GenericELTransformer[T]` is the base; `RequirementsELTransformer` and `SVCsELTransformer` are thin subclasses.

### Validation (`common/validators/`)
- `syntax_validator.py` — JSON Schema validation against `resources/schemas/v1/`
- `semantic_validator.py` — post-parse cross-reference checks (SVC refs valid reqs, annotations ref valid IDs, MVRs ref valid SVCs)
- `lifecycle_validator.py` — warns when DEPRECATED/OBSOLETE items are still referenced

### Commands (`commands/`)
Three commands, each consuming a `CombinedIndexedDataset`:
- `report-asciidoc` — Jinja2 template rendering (`common/jinja2.py`) → AsciiDoc
- `generate-json` — JSON serialization via `jsonpickle`
- `status` — tabular summary, exit code = number of unmet requirements

## Key Conventions

- **URN format**: `some:urn:string` — the separator is `:`. `UrnId` is the canonical composite key used throughout indexes.
- **`@Requirements("REQ_xxx")`** decorator from `reqstool-python-decorators` annotates methods that implement a requirement. This is how the tool tracks its own requirement coverage.
- Data flows are uni-directional: raw parsing → indexing → output. Mutation only happens inside generators before the final `CombinedIndexedDataset` is frozen.
- `assert` statements are used for invariant checks in the generators (not for user-facing validation).
- Tests under `tests/unit` use file-based fixtures from `tests/resources/`.
