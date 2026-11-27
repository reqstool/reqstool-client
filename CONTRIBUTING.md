# Contributing to reqstool-client

Thank you for your interest in contributing!

For DCO sign-off, commit conventions, and code review process, see the organization-wide [CONTRIBUTING.md](https://github.com/reqstool/.github/blob/main/CONTRIBUTING.md).

## Prerequisites

- Python 3.10+
- [Hatch](https://hatch.pypa.io/) (`pip install hatch`)
- [reqstool](https://github.com/reqstool/reqstool-client) (`pipx install reqstool`) — for dogfooding
  this repo's own traceability data against the latest PyPI release; use `hatch run dev:...` below
  to exercise your local changes instead
- [OpenSpec](https://github.com/Fission-AI/OpenSpec) (`npm install -g @fission-ai/openspec`)

## Setup

```bash
git clone https://github.com/reqstool/reqstool-client.git
cd reqstool-client
hatch env create dev
```

If using Claude Code, opening this repo will prompt you to confirm adding the `reqstool-ai`
marketplace and enabling the `reqstool`/`reqstool-openspec` plugins (configured in
`.claude/settings.json`) — accept the prompt.

Then regenerate the `opsx` slash commands and OpenSpec skills
(`.claude/commands/opsx/`, `.claude/skills/openspec-*`) — they're CLI-generated tool scaffolding,
not committed to the repo:

```bash
openspec update   # or: openspec init --tools claude --force
```

## Build & Test

```bash
# Run all tests
hatch run dev:pytest --cov=reqstool

# Unit tests only
hatch run dev:pytest --cov=reqstool tests/unit

# Integration tests only
hatch run dev:pytest --cov=reqstool tests/integration
```

## Linting & Formatting

```bash
# Format with black
hatch run dev:black src tests

# Lint with flake8
hatch run dev:flake8
```

## Risk paths

Changes to these paths need a mutation or property test in addition to the usual tests, and the
PR's Checks section says whether it ran:

| Path | Why |
|------|-----|
| `src/reqstool/services/statistics_service.py` | the single requirement "complete" verdict (#411) |
| `src/reqstool/model_generators/testdata_model_generator.py` | JUnit status mapping (#494) |
| `src/reqstool/common/utils.py` (`to_file_uri`, `uri_to_path`, `strip_windows_extended_length_prefix`), `src/reqstool/lsp/workspace_manager.py` | path and URI normalisation (#457) |
| `src/reqstool/storage/el_to_sql_compiler.py` | filter expressions compiled into SQL |

Neither Hypothesis nor a mutation tool is a project dependency yet. Install one ad hoc in the dev
environment (for example `hatch run dev:pip install hypothesis mutmut`) and say which one you used.

## Model Generation

Pydantic data models in `src/reqstool/models/generated/` are auto-generated from the JSON Schemas
in `src/reqstool/resources/schemas/v1/`. **JSON Schema is the source of truth** — never edit the
generated files directly.

To regenerate after modifying a schema:

```bash
hatch run dev:codegen
```

This runs `datamodel-codegen` to produce Pydantic v2 `BaseModel` classes from all schema files.
The generated files should be committed alongside the schema changes.
