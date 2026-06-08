# Pass 1 — Discovery map: `commands/` domain

**Method:** Claude-direct (read `src/reqstool/command.py` + command impls, reconciled against the
existing SSOT at `docs/reqstool/`).
**Date:** 2026-06-08

## Key reframe

This project **already dogfoods reqstool**. The SSOT exists at `docs/reqstool/`:
`requirements.yml` (REQ_001–REQ_038), `software_verification_cases.yml` (SVC_001–SVC_038),
`manual_verification_results.yml`. Code carries `@Requirements("REQ_xxx")` annotations.

So Pass 1 is **not** "invent requirements" — it's **map command behavior → existing IDs and
surface the gaps** (behaviors shipped in the CLI with no requirement, or annotations with no SSOT
entry). Pass 2 becomes "fill the gaps," not "author from scratch."

## Command surface → existing coverage

| Command | Behavior (from argparse + impl) | Existing REQ | Existing SVC |
|---------|----------------------------------|--------------|--------------|
| `report` | generate report; `--group-by`, `--sort-by`, `-o` | REQ_032, REQ_033, REQ_034, REQ_035 | SVC_029–035 |
| `report --format markdown` | markdown output (newer) | — (REQ_032 predates `--format`) | — |
| `report-asciidoc` | deprecated alias | n/a (deprecation, not a req) | — |
| `export` (json) | JSON export (was `generate-json`) | REQ_030, REQ_031 | SVC_027, SVC_028 |
| `export --req-ids/--svc-ids` | filter export output | — | — |
| `export --no-filters` | skip filtering | — | — |
| `export --format sqlite` | dump SQLite DB to file | — | — |
| `validate` | spec completeness; `--strict`; exit codes | — | — |
| `status` (core) | status + statistics; `-o` | REQ_027, REQ_028, REQ_029 | SVC_021–026 |
| `status --verbosity` | compact/normal/verbose/extra-verbose | — | — |
| `status --incomplete` | show only incomplete | — | — |
| `status --check-all-reqs-met` | exit 200 if any unmet | — | — |
| `status --format json` | JSON status | — | — |
| `status --with-post-tests` | post-build test gating | — | — |
| `enrich` | enrich doc w/ titles; `--preset`, `--input` | REQ_039 *(annotated, not in SSOT)* | — |
| `lsp` | start LSP server | `REQ-001` *(hyphen scheme — separate)* | `SVC-001` |
| `mcp` | start MCP server; auto-detect config | — | — |

## Gaps surfaced (candidates for Pass 2)

| # | Gap | Type | Notes |
|---|-----|------|-------|
| G1 | `validate` command | **missing req** | Whole command (spec-completeness check + `--strict` + exit codes) has no requirement. |
| G2 | `export --format sqlite` | **missing req** | REQ_030/031 cover JSON only; SQLite dump is uncovered. |
| G3 | `enrich` / REQ_039 | **orphan annotation** | `@Requirements("REQ_039")` in `command.py:631` + `enrich.py:13`, but REQ_039 absent from `requirements.yml` (ends at 038). No SVC. |
| G4 | `mcp` command | **missing req** | No requirement for serving the dataset over MCP. |
| G5 | `status` newer flags | **partial** | `--verbosity`, `--incomplete`, `--check-all-reqs-met` (exit 200), `--format json`, `--with-post-tests` (post-build gating) — none have dedicated reqs. |
| G6 | `report --format markdown` | **partial** | REQ_032 is format-agnostic ("generate a report"); decide whether markdown warrants its own req or a description tweak. |
| G7 | `export` filters | **partial** | `--req-ids` / `--svc-ids` / `--no-filters` selective export — uncovered. |
| G8 | `lsp` ID scheme | **convention drift** | `REQ-001` / `SVC-001` (hyphens) vs the `REQ_`/`SVC_` underscore SSOT. Inconsistent; likely a placeholder. Not in main set. |

## Observations / judgment notes

- **G3 (REQ_039) is the cleanest real gap** — code already commits to the ID; SSOT just needs the
  entry + an SVC. Lowest-risk Pass 2 starting point.
- **G1/G2/G4** are genuine new user-facing capabilities (validate, sqlite export, mcp) — legitimate
  `shall`/`should` requirements, not implementation detail.
- **G5/G7** are flag-level behaviors. Risk of over-minting requirements per CLI flag. Recommend
  folding most into the parent command's requirement *description* rather than new IDs — except
  `--check-all-reqs-met` (the exit-code-200 gating contract) and `--with-post-tests` (post-build
  gating) which are distinct behavioral contracts worth their own reqs.
- **G8** is a hygiene fix, not a new requirement — flag for the LSP domain pass, not commands.
- Lower domains (`storage/`, `locations/`, generators) correctly fold up: e.g. REQ_001/002/003
  (local/git/maven indata) live in `locations/` but are framed as system capabilities. Confirms the
  "requirements at behavior altitude" slice.
