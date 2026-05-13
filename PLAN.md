# Implementation Plan: `enrich` Command + MCP Tool (Issue #352)

## Context

OpenSpec files using the reqstool integration reference requirements via opaque IDs
(e.g. `CORE_0004`, `SVC_CLI_0003`), keeping specs DRY. In a plain-text viewer these
IDs are unreadable without context. The `enrich` command (and matching MCP tool)
resolves those IDs from the loaded requirements database and injects titles and
further fields inline, making specs human-readable while reqstool remains the
single source of truth.

**Scope**: one-shot CLI command + MCP tool. No preset customisation. No `--fields`
flag. Daemon mode (`--stdio`) deferred to a follow-up.

---

## Command Interface

```
reqstool enrich --preset <name> [--input <file>] [-o <file>] [source]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--preset NAME` | **required** | Built-in preset name (see below) |
| `--input / -i FILE` | stdin | Input file to enrich |
| `-o / --output FILE` | stdout | Output file |
| `source` | auto-detect | Optional location sub-command (`local -p <path>`, `git`, `maven`, `pypi`). If omitted, walks up from cwd until `.reqstool-ai.yaml` is found (same as `reqstool mcp`). |

---

## Built-in Presets

| Preset | Trigger | Fields | Drop stubs |
|--------|---------|--------|------------|
| `openspec:spec` | colon-header | all | yes |
| `openspec:delta-spec` | colon-header | all | yes |
| `openspec:design` | inline | title only | no |
| `openspec:proposal` | inline | title only | no |
| `openspec:tasks` | inline | title only | no |

`openspec:delta-spec` is a named preset with identical behaviour to `openspec:spec`.
All presets skip inline backtick spans and fenced code blocks.

---

## Injection Algorithm

### Trigger: colon-header (`openspec:spec`, `openspec:delta-spec`)

1. Pre-scan: mark no-inject zones (inline backtick spans, fenced code blocks).
2. For each line:
   - If inside a fenced block → pass through unchanged.
   - If line matches `.*:\s+<ID>\s*$` (ID is last token, preceded by colon) and
     the ID is known and not in a backtick span → inject enrichment block (see below).
   - If line matches the stub pattern for the same ID just enriched → **drop** it.
   - Otherwise → pass through unchanged.

**Stub pattern**: `^\s*The system SHALL (implement|pass)\s+<ID>\.?\s*$`

### Trigger: inline (`openspec:design`, `openspec:proposal`, `openspec:tasks`)

1. Pre-scan: mark no-inject zones (inline backtick spans, fenced code blocks).
2. For each line:
   - Find **all** occurrences of known IDs not inside no-inject zones.
   - Process matches **right-to-left** (to preserve string positions).
   - For each match: append ` — <title>` immediately after the ID.
   - Every occurrence across the entire document is enriched (no deduplication).

---

## Enrichment Output Format

### Title injection (both triggers, all presets)

Appended inline immediately after the matched ID:

```
### Requirement: CORE_0004 — Detect Build System
```

For MVRs (no title field), the inline slot uses pass/fail:

```
#### Result: MVR_001 — PASSED
```

### Block injection (colon-header trigger only)

One `> **Label**: value` line per field, in canonical order, omitting null/empty fields.

**REQ** field order: Significance → Description → Rationale → Categories → References →
Implementation → Revision → Lifecycle

**SVC** field order: Description → Verification → Instructions → Requirements →
Revision → Lifecycle

**MVR** field order: Comment → SVCs

```
### Requirement: CORE_0004 — Detect Build System
> **Significance**: SHALL
> **Description**: The tool shall detect whether the target project uses Gradle or Maven
> **Rationale**: All scanning operations depend on knowing the build system
> **Categories**: Functional Suitability
> **References**: CORE_0001, CORE_0002
> **Implementation**: In Code
> **Revision**: 0.1.0
> **Lifecycle**: Effective

#### Scenario: SVC_CORE_0004 — Build System Detection Test
> **Description**: Test that the scanner correctly identifies Gradle and Maven projects
> **Verification**: Automated Test
> **Requirements**: CORE_0004
> **Lifecycle**: Effective

#### Result: MVR_001 — PASSED
> **Comment**: Verified manually on 2026-01-15
> **SVCs**: SVC_CORE_0001, SVC_CORE_0002
```

### Value formatting

- Single-word enum values → uppercase: `SHALL`, `EFFECTIVE`, `PASSED`, `FAILED`
- Hyphenated enum values → title-case with spaces: `Automated Test`, `Manual Test`,
  `Functional Suitability`, `Interaction Capability`, `In Code`
- List values → comma-separated on one line: `CORE_0001, CORE_0002`

---

## Shared Processing Module

All text-enrichment logic lives in one module used by both the CLI command and the
MCP tool:

```
src/reqstool/common/enrichment/
    __init__.py
    enricher.py
```

### `enricher.py` public surface

```python
@dataclass(frozen=True)
class EnrichmentConfig:
    trigger: str              # 'colon-header' | 'inline'
    title_only: bool          # True → skip block injection
    drop_stubs: bool
    skip_code_spans: bool     # always True for PoC

BUILT_IN_PRESETS: dict[str, EnrichmentConfig] = {
    'openspec:spec':       EnrichmentConfig('colon-header', False, True,  True),
    'openspec:delta-spec': EnrichmentConfig('colon-header', False, True,  True),
    'openspec:design':     EnrichmentConfig('inline',       True,  False, True),
    'openspec:proposal':   EnrichmentConfig('inline',       True,  False, True),
    'openspec:tasks':      EnrichmentConfig('inline',       True,  False, True),
}

def enrich_text(
    text: str,
    requirements: dict[UrnId, RequirementData],
    svcs: dict[UrnId, SVCData],
    mvrs: dict[UrnId, MVRData],
    config: EnrichmentConfig,
) -> str: ...
```

Internal helpers (module-level, tested independently):
- `_build_lookup(requirements, svcs, mvrs)` → `dict[str, tuple[str, ...]]`
- `_make_pattern(lookup)` → `re.Pattern` (single alternation, sorted by length desc)
- `_mark_no_inject_zones(text)` → list of `(start, end)` character ranges
- `_format_block(entity, fields)` → `list[str]` of `> **Label**: value` lines
- `_format_value(value)` → applies uppercase/title-case rules

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
    spec_all_fields/
        input.md
        expected.md        ← colon-header, all fields, stubs dropped
    spec_no_description/
        input.md
        expected.md        ← SVC with no description: no block lines emitted
    inline_title_only/
        input.md
        expected.md        ← inline mode, multiple IDs per line, every occurrence
    inline_code_spans/
        input.md
        expected.md        ← IDs inside backticks and fenced blocks skipped
    no_ids/
        input.md
        expected.md        ← identical to input (full passthrough)
    mvr/
        input.md
        expected.md        ← MVR inline PASSED/FAILED + comment/svc_ids block
```

---

## `EnrichCommand` Skeleton

```python
@Requirements("REQ_XXX")  # next available from docs/reqstool/requirements.yml
class EnrichCommand:
    def __init__(
        self,
        location: LocationInterface,
        input_content: str,
        config: EnrichmentConfig,
    ):
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
            mvrs = repo.get_all_mvrs()
        return enrich_text(self.__input_content, requirements, svcs, mvrs, self.__config)
```

---

## MCP Tool

```python
@mcp.tool()
def enrich_document(content: str, preset: str) -> str:
    """Enrich an OpenSpec document by resolving requirement/SVC/MVR IDs.

    Injects titles and further fields next to each known ID according to the
    named preset. Both arguments are required.

    Presets: openspec:spec, openspec:delta-spec, openspec:design,
             openspec:proposal, openspec:tasks
    """
    if preset not in BUILT_IN_PRESETS:
        raise ValueError(f"Unknown preset {preset!r}. "
                         f"Valid: {sorted(BUILT_IN_PRESETS)}")
    config = BUILT_IN_PRESETS[preset]
    return enrich_text(content, repo.get_all_requirements(),
                       repo.get_all_svcs(), repo.get_all_mvrs(), config)
```

`repo` is the `RequirementsRepository` already built at MCP server startup.

---

## openspecui Hook (reference — not built in this PR)

```typescript
// openspec/openspecui.hooks.ts
let client: Client | null = null

export const onReadDocument: OnReadDocumentHookV1 = async (ctx, read) => {
  if (!client) {
    const transport = new StdioClientTransport({
      command: 'reqstool', args: ['mcp'], cwd: ctx.projectDir,
    })
    client = new Client({ name: 'openspecui', version: '1.0' }, {})
    await client.connect(transport)
    ctx.lifecycle.onDispose(async () => { await client?.close(); client = null })
  }
  const result = await read()
  const kind = ctx.document.kind === 'delta-spec' ? 'spec' : ctx.document.kind
  const enriched = await client.callTool('enrich_document', {
    content: result.markdown,
    preset: `openspec:${kind}`,
  })
  return { ...result, markdown: enriched.content[0].text }
}
```

---

## `command.py` Changes

**Import** (after existing command imports):
```python
from reqstool.commands.enrich.enrich import EnrichCommand
from reqstool.common.enrichment.enricher import BUILT_IN_PRESETS, EnrichmentConfig
```

**Argparse** (after `status_source_subparsers`, before `# command: lsp`):
```python
enrich_parser = subparsers.add_parser(
    "enrich",
    help="Enrich a document with requirement/SVC/MVR titles and descriptions. "
         "Auto-detects dataset from .reqstool-ai.yaml if no source is given.",
)
enrich_parser.add_argument(
    "--preset", required=True,
    choices=sorted(BUILT_IN_PRESETS),
    help="Enrichment preset (e.g. openspec:spec, openspec:design)",
)
enrich_parser.add_argument("--input", "-i", metavar="FILE", default=None,
                           help="Input file (default: stdin)")
self._add_argument_output(enrich_parser)
enrich_source_subparsers = enrich_parser.add_subparsers(dest="source", required=False)
self._add_subparsers_source(enrich_source_subparsers,
                            include_report_options=False,
                            include_filter_options=False)
```

**`command_enrich` method** (after `command_mcp`):
- Same auto-detection pattern as `command_mcp`
- Read stdin if `--input` not given
- Look up `BUILT_IN_PRESETS[enrich_args.preset]` → `EnrichmentConfig`
- Instantiate `EnrichCommand`, write `result.result` to output

**Routing** in `main()`:
```python
elif args.command == "enrich":
    command.command_enrich(enrich_args=args)
```

---

## Verification

```bash
# Unit tests (pure helpers, no DB)
hatch run dev:pytest tests/unit/reqstool/common/enrichment/

# Integration tests
hatch run dev:pytest tests/unit/reqstool/commands/enrich/

# Full suite
hatch run dev:pytest --cov=reqstool tests/unit

# Format + lint
hatch run dev:black src tests && hatch run dev:flake8

# Smoke — spec preset
echo "### Requirement: REQ_101
The system SHALL implement REQ_101." | \
  hatch run python src/reqstool/command.py enrich --preset openspec:spec \
    local -p tests/resources/test_data/data/local/test_basic/baseline/ms-101

# Smoke — inline preset
echo "This implements REQ_101 and verifies SVC_201." | \
  hatch run python src/reqstool/command.py enrich --preset openspec:design \
    local -p tests/resources/test_data/data/local/test_basic/baseline/ms-101
```

---

## Follow-up Issues to Create

- **reqstool-ai**: Implement the openspecui hook (`openspec/openspecui.hooks.ts`) that
  starts `reqstool mcp` once per project session and calls `enrich_document` per document
  read. Reference the hook skeleton in this plan's "openspecui Hook" section.

---

## Notes

- `REQ_XXX` placeholder: check next available number in `docs/reqstool/requirements.yml`.
- `openspec:delta-spec` is a named preset with identical behaviour to `openspec:spec`;
  the alias mapping (`delta-spec` → spec behaviour) lives in `BUILT_IN_PRESETS`, not
  in the hook.
- MVR enrichment: inline slot = `PASSED`/`FAILED`; block fields = Comment, SVCs.
- `--fields` flag deferred (no raw field selection in PoC).
- Daemon mode (`--stdio`) deferred.
- The openspecui hook (TypeScript) is documented here for reference but is not part
  of this PR.
