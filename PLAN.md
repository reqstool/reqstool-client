# Implementation Plan: `enrich` Command + MCP Tool (Issue #352)

## Context

OpenSpec files using the reqstool integration reference requirements via opaque IDs
(e.g. `CORE_0004`, `SVC_CLI_0003`), keeping specs DRY. In a plain-text viewer these
IDs are unreadable without context. The `enrich` command (and matching MCP tool)
resolves those IDs from the loaded requirements database and injects titles and
optionally further fields inline, making specs human-readable while reqstool remains
the single source of truth.

**Scope**: one-shot CLI command + MCP tool. Daemon mode (`--stdio`) is deferred to a follow-up.

---

## Command Interface

```
reqstool enrich [--input <file>] [-o <file>] [--fields <field,...>] [source]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--input / -i FILE` | stdin | Input file to enrich |
| `-o / --output FILE` | stdout | Output file |
| `--fields FIELDS` | `title` | Comma-separated fields to inject. `all` is a shorthand for every field. |
| `source` | auto-detect | Optional location sub-command (`local -p <path>`, `git`, `maven`, `pypi`). If omitted, walks up from cwd until `.reqstool-ai.yaml` is found (same pattern as `reqstool mcp`). |

### `--fields` values

**Requirements**

| Field | Description |
|-------|-------------|
| `title` | Injected inline after the ID: `ID — Title` |
| `significance` | SHALL / SHOULD / MAY |
| `description` | Requirement text |
| `rationale` | Why the requirement exists |
| `categories` | e.g. `functional-suitability` |
| `references` | Related requirement IDs |
| `implementation` | `in-code` or `N/A` |
| `revision` | Semver string |
| `lifecycle` | `effective` / `deprecated` / `obsolete` / `draft` |

**SVCs**

| Field | Description |
|-------|-------------|
| `title` | Injected inline after the ID: `ID — Title` |
| `description` | SVC text |
| `verification` | `automated-test` / `manual-test` / `review` / `platform` / `other` |
| `instructions` | How to verify |
| `requirement_ids` | Requirements this SVC covers |
| `revision` | Semver string |
| `lifecycle` | State |

**MVRs**

MVR has no `title` field. The inline slot uses pass/fail status instead: `MVR_001 — PASSED` / `MVR_001 — FAILED`.

| Field | Description |
|-------|-------------|
| `passed` | Injected inline: `PASSED` or `FAILED` |
| `comment` | Free-text verification comment |
| `svc_ids` | SVCs covered by this MVR |

`--fields all` includes every field above that has a non-null value.

---

## Injection Algorithm

### Two injection strategies — determined by whether `--fields` includes anything beyond `title`

**Title-only** (`--fields title`, the default):
- Scan every line for known IDs.
- For each line: append ` — <title>` after the **rightmost** ID occurrence.
- Stub lines (`The system SHALL implement/pass <ID>.`) pass through unchanged.
- Works for all file types (spec.md, design.md, proposal.md, tasks.md).

**Full** (`--fields` includes description or more):
- Only inject on **colon-header lines** — lines matching `.*:\s+<ID>\s*$`
  (e.g. `### Requirement: CORE_0004`, `#### Scenario: SVC_CORE_0004`).
- After an enriched header line, emit `> **Field**: value` lines for each
  requested field that is present (see output format below).
- **Stub lines** immediately following an enriched header are **dropped**.
  A stub is any line where the same ID appears and the line contains no other
  significant content beyond the ID itself (detected via the same pattern match
  used in title-only mode on the subsequent line).
- Non-header lines and lines with no known ID pass through unchanged.

### Stub detection

A stub matches: `^\s*The system SHALL (implement|pass)\s+<ID>\.?\s*$`

### Output format — enriched block (one `> ` line per field)

```
### Requirement: CORE_0004 — Detect Build System
> **Significance**: SHALL
> **Description**: The tool shall detect whether the target project uses Gradle or Maven
> **Rationale**: All scanning operations depend on knowing the build system
> **Categories**: functional-suitability
> **References**: CORE_0001
> **Lifecycle**: effective

#### Scenario: SVC_CORE_0004 — Build System Detection Test
> **Description**: Test that the scanner correctly identifies Gradle and Maven projects
> **Verification**: automated-test
> **Requirements**: CORE_0004
> **Lifecycle**: effective
```

Fields with null/empty values are omitted silently.

---

## Shared Processing Module

All text-enrichment logic lives in one module, shared between the CLI command and
the MCP tool:

```
src/reqstool/common/enrichment/
    __init__.py
    enricher.py          ← _build_lookup, _make_pattern, _enrich_text, EnrichmentConfig
```

`EnrichmentConfig` dataclass:
```python
@dataclass(frozen=True)
class EnrichmentConfig:
    fields: frozenset[str]  # e.g. frozenset({"title", "description"})
```

`EnrichmentConfig.from_fields_arg("title,description")` parses the CLI string.
`EnrichmentConfig.all()` returns the full field set.

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `src/reqstool/common/enrichment/__init__.py` | Create (empty) |
| `src/reqstool/common/enrichment/enricher.py` | Create — shared logic |
| `src/reqstool/commands/enrich/__init__.py` | Create (empty) |
| `src/reqstool/commands/enrich/enrich.py` | Create — `EnrichCommand` (thin wrapper) |
| `src/reqstool/mcp/server.py` | Modify — add `enrich_document` tool |
| `src/reqstool/command.py` | Modify — argparse, `command_enrich`, routing |
| `tests/unit/reqstool/common/enrichment/` | Create — unit tests for `enricher.py` |
| `tests/unit/reqstool/commands/enrich/` | Create — integration tests |
| `tests/resources/enrich/` | Create — static input/output fixture files |

---

## Static Test Fixtures

```
tests/resources/enrich/
    spec_title_only/
        input.md
        expected.md
    spec_full/
        input.md
        expected.md
    inline_title_only/
        input.md
        expected.md
    no_ids/
        input.md
        expected.md      ← identical to input (passthrough)
```

Test cases to cover:
1. Spec header line → title injected inline
2. Spec header + stub → stub removed, full block injected (`--fields all`)
3. Multiple IDs in one document, each enriched independently
4. Line with unknown ID → passes through unchanged
5. Line with no ID → passes through unchanged
6. SVC with no description → title injected, no description line emitted
7. Inline mid-sentence ID (`--fields title` on design.md) → title appended after ID
8. `--fields all` on a file with no colon-header lines → no enrichment (no header matches)

---

## `EnrichCommand` Skeleton

```python
@Requirements("REQ_XXX")  # next available from docs/reqstool/requirements.yml
class EnrichCommand:
    def __init__(self, location: LocationInterface, input_content: str,
                 config: EnrichmentConfig):
        self.__initial_location = location
        self.__input_content = input_content
        self.__config = config
        self.result: str = self.__run()

    def __run(self) -> str:
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ) as (db, _):
            repo = RequirementsRepository(db)
            requirements = repo.get_all_requirements()
            svcs = repo.get_all_svcs()
        return enrich_text(self.__input_content, requirements, svcs, self.__config)
```

---

## MCP Tool

New tool added to `src/reqstool/mcp/server.py`:

```python
@mcp.tool()
def enrich_document(content: str, fields: str = "title") -> str:
    """Enrich an OpenSpec document by resolving requirement/SVC IDs.

    Injects titles (and optionally further fields) inline next to each known ID.
    Use fields='all' to include all available fields.
    """
    config = EnrichmentConfig.from_fields_arg(fields)
    return enrich_text(content, _session.requirements, _session.svcs, config)
```

`_session` is the existing `ProjectSession` already loaded at MCP server startup.

---

## `command.py` Changes

**Import** (after existing command imports):
```python
from reqstool.commands.enrich.enrich import EnrichCommand
```

**Argparse** (after `status_source_subparsers`, before `# command: lsp`):
```python
enrich_parser = subparsers.add_parser(
    "enrich",
    help="Enrich a document with requirement/SVC titles and descriptions. "
         "Auto-detects dataset from .reqstool-ai.yaml if no source is given.",
)
enrich_parser.add_argument("--input", "-i", metavar="FILE", default=None,
                           help="Input file (default: stdin)")
enrich_parser.add_argument("--fields", default="title",
                           help="Fields to inject: title,description,... or 'all' (default: title)")
self._add_argument_output(enrich_parser)
enrich_source_subparsers = enrich_parser.add_subparsers(dest="source", required=False)
self._add_subparsers_source(enrich_source_subparsers,
                            include_report_options=False, include_filter_options=False)
```

**`command_enrich` method** (after `command_mcp`):
- Same auto-detection pattern as `command_mcp` (find_config → resolve_system_path → LocalLocation)
- Read stdin if `--input` not given
- Parse `--fields` into `EnrichmentConfig`
- Instantiate `EnrichCommand`, write `result.result` to output

**Routing** in `main()`:
```python
elif args.command == "enrich":
    command.command_enrich(enrich_args=args)
```

---

## Verification

```bash
# Unit tests (pure, no DB)
hatch run dev:pytest tests/unit/reqstool/common/enrichment/

# Integration tests
hatch run dev:pytest tests/unit/reqstool/commands/enrich/

# Full suite
hatch run dev:pytest --cov=reqstool tests/unit

# Format + lint
hatch run dev:black src tests && hatch run dev:flake8

# Smoke — title only (default)
echo "### Requirement: REQ_101" | \
  hatch run python src/reqstool/command.py enrich \
    local -p tests/resources/test_data/data/local/test_basic/baseline/ms-101

# Smoke — all fields
echo "### Requirement: REQ_101" | \
  hatch run python src/reqstool/command.py enrich --fields all \
    local -p tests/resources/test_data/data/local/test_basic/baseline/ms-101
```

---

## Notes

- `REQ_XXX` placeholder: verify next available REQ number in `docs/reqstool/requirements.yml`.
- MVR enrichment is supported. Inline slot uses `PASSED`/`FAILED` (no title field). Requires `repo.get_all_mvrs()` in the lookup build.
- Daemon mode (`--stdio`) is out of scope for this PR.
- The `enrich_text` function in `enricher.py` is the single implementation used by
  both `EnrichCommand` and the MCP `enrich_document` tool.
