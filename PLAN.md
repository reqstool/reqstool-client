# Implementation Plan: `render` Command (Issue #352)

## Context

Reqstool spec files use opaque IDs (e.g. `CLI_0003`, `SVC_CLI_0003`) to reference
requirements, keeping specs DRY. In a plain-text viewer these IDs are unreadable
without context. The `render` command resolves those IDs from the loaded requirements
database and injects title + description inline, making specs human-readable while
reqstool remains the single source of truth.

**Scope**: One-shot mode only. Daemon mode (`--stdio`) is deferred to a follow-up.

## Files to Create / Modify

| File | Action |
|------|--------|
| `src/reqstool/commands/render/__init__.py` | Create (empty, copyright header) |
| `src/reqstool/commands/render/render.py` | Create — `RenderCommand` + helpers |
| `src/reqstool/command.py` | Modify — argparse, `command_render`, routing |
| `tests/unit/reqstool/commands/render/__init__.py` | Create (empty) |
| `tests/unit/reqstool/commands/render/test_render.py` | Create — unit + integration tests |

## Command Interface

```
reqstool render [--input <file>] [-o <file>] [source]
```

- `--input / -i FILE` — input file to enrich; defaults to stdin if omitted
- `-o / --output FILE` — output file; defaults to stdout
- `source` — optional location sub-command (`local -p <path>`, `git`, `maven`, `pypi`);
  if omitted, auto-detects the dataset by walking up from cwd until `.reqstool-ai.yaml`
  is found (same pattern as `reqstool mcp`)

## Transformation Example

Input:
```
### Requirement: CLI_0003

#### Scenario: SVC_CLI_0003
```

Output:
```
### Requirement: CLI_0003 — CLI Recipe Execution
> The tool shall execute recipes via CLI subcommand

#### Scenario: SVC_CLI_0003 — Execute recipe via CLI
> GIVEN a project directory with Java sources
> WHEN the user runs `atunko run -r <recipe> --project-dir <path>`
> THEN the recipe is executed against the project and results are reported
```

## Algorithm

1. Build lookup `{bare_id: (title, description)}` from all requirements + SVCs.
2. Compile a single alternation regex (sorted by length desc) with word boundaries.
3. For each input line:
   - If no known ID found → pass through unchanged.
   - Otherwise take the **rightmost** match, append ` — <title>` inline, then insert
     `> <description>` line(s) after (each description line prefixed with `> `).

## `render.py` Skeleton

```python
@Requirements("REQ_XXX")  # replace with next available REQ from docs/reqstool/requirements.yml
class RenderCommand:
    def __init__(self, location: LocationInterface, input_content: str):
        self.__initial_location = location
        self.__input_content = input_content
        self.result: str = self.__run()

    def __run(self) -> str:
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ) as (db, _):
            repo = RequirementsRepository(db)
            requirements = repo.get_all_requirements()
            svcs = repo.get_all_svcs()
        return _enrich_text(self.__input_content, requirements, svcs)
```

Helper functions (module-level, tested independently):
- `_build_lookup(requirements, svcs) -> dict[str, tuple[str, Optional[str]]]`
- `_make_pattern(lookup) -> re.Pattern`  — single alternation, sorted by length desc
- `_format_description(description) -> list[str]`  — each line prefixed with `> `
- `_enrich_text(text, requirements, svcs) -> str`  — main scan-and-inject loop

## `command.py` Changes

### Import (after line 35)
```python
from reqstool.commands.render.render import RenderCommand
```

### Argparse (between lines 294–296, after `status_source_subparsers`, before `# command: lsp`)
```python
# command: render
render_parser = subparsers.add_parser("render", help="Enrich a document with requirement/SVC titles and descriptions. ...")
render_parser.add_argument("--input", "-i", metavar="FILE", default=None, help="Input file to enrich (default: stdin)")
self._add_argument_output(render_parser)
render_source_subparsers = render_parser.add_subparsers(dest="source", required=False)
self._add_subparsers_source(render_source_subparsers, include_report_options=False, include_filter_options=False)
```

### `command_render` method (after `command_mcp` ends, before `print_help`)
Same auto-detection pattern as `command_mcp` (lines 461–488):
- `find_config()` → `resolve_system_path()` → `LocalLocation`
- Read stdin if `--input` not provided
- Instantiate `RenderCommand`, write `result.result` to `render_args.output`

### Routing in `main()` (after `elif args.command == "mcp":`)
```python
elif args.command == "render":
    command.command_render(render_args=args)
```

## Tests

Fixture: `test_basic/baseline/ms-101`
- `REQ_101`: title `"Title REQ_101"`, description `"Description REQ_101"`
- `SVC_101`: title `"Some Title SVC_101"`, no description
- `SVC_201`: title `"Some Title SVC_201"`, description `"Some Description SVC_201"`

Test cases:
1. Pure unit: `_format_description(None/empty/single-line/multi-line/blank-lines)`
2. REQ with description: title appended inline + blockquote after
3. SVC without description: title appended, no blockquote emitted
4. SVC with description: both title and blockquote
5. Unknown ID: line passes through unchanged
6. No ID: line passes through unchanged
7. Multi-ID document: each ID line enriched independently
8. Interspersed plain lines preserved exactly

## Verification

```bash
# Unit tests
hatch run dev:pytest tests/unit/reqstool/commands/render/

# Full suite (no regressions)
hatch run dev:pytest --cov=reqstool tests/unit

# Format + lint
hatch run dev:black src tests
hatch run dev:flake8

# Manual smoke (explicit source)
echo "### Requirement: REQ_101" | \
  hatch run python src/reqstool/command.py render local \
    -p tests/resources/test_data/data/local/test_basic/baseline/ms-101
```

## Notes

- `REQ_XXX` placeholder: verify next available REQ number in `docs/reqstool/requirements.yml`
  before writing the decorator.
- SVC fixture file is `software_verification_cases.yml` (not `svcs.yml`) — no impact on tests.
- Daemon mode (`--stdio`) is out of scope for this PR.
