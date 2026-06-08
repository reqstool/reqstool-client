# PLAN: OpenSpec + reqstool bootstrap

Tracking doc for building an OpenSpec specification of the `reqstool-client` codebase, then
deriving reqstool data (requirements, SVCs, MVRs) from it in a later pass.

**Branch:** `worktree-feat+openspec-reqstool-bootstrap` (worktree)
**Status:** 🟡 In progress — Passes 2 & 3 done (12 specs / 71 reqs, all validate strict); next is Pass 4 (the flip)
**Owner:** Jimisola Laursen

---

## Direction: OpenSpec-first (decided 2026-06-08)

Build the **OpenSpec layer first as the SSOT**, author content-rich specs of current behavior,
then **derive reqstool data from it in a later "flip" pass**. This reverses the reqstool-ai
plugin's default (reqstool-is-SSOT) on purpose, for the buildup phase only.

### Why this works (and where my earlier objection failed)

My objection — "you can't derive reqstool from OpenSpec" — only applied to *thin* reference specs.
Here OpenSpec is SSOT during buildup, so specs are **content-rich** (real requirement text +
scenarios). That content is exactly what the later pass distills reqstool from. Objection dissolved.

### Conditions to keep it working

1. **Author content-rich specs**, not thin reference stubs — the later derivation depends on it.
2. **The OpenSpec→reqstool derivation is curated, not mechanical** — `significance` (shall/should/
   may), ISO-25010 `categories`, and SVC GIVEN/WHEN/THEN structure are judgment calls.
3. **Explicit SSOT flip point** (Pass 4): ownership moves to reqstool, the 21 source-file
   annotations get rewritten, specs get thinned to references. Until then CI's reqstool gate is red
   on this branch. **Accepted** (clean slate).

Out of scope for automated derivation: **MVRs** (human attestations).

---

## Clean slate (done 2026-06-08)

- Deleted project SSOT: `docs/reqstool/` (requirements.yml, software_verification_cases.yml,
  manual_verification_results.yml, reqstool_config.yml). Reversible on branch via git.
- Kept (separate, not the SSOT): `tests/fixtures/`, `tests/resources/`, `docs/modules/examples/`.
- `openspec init --tools claude` → `openspec/{specs,changes,changes/archive}/` + `.claude` skills/
  commands (`/opsx:propose`, `apply`, `archive`, `explore`). OpenSpec CLI 1.3.1.

---

## Blast radius (known, accepted)

- `.github/workflows/build.yml:44` runs `reqstool status local -p docs/reqstool` → **CI red** until
  Pass 4 regenerates reqstool data.
- `pyproject.toml:81` `dataset_directory = "docs/reqstool"` → re-point or restore in Pass 4.
- 21 source files carry `@Requirements`/`@SVCs` annotations → re-annotated in Pass 4 (the flip).

---

## Passes

| Pass | Description | Model | Status | Output |
|------|-------------|-------|--------|--------|
| 0 | Setup: worktree + plan doc | — | ✅ done | this file |
| 1 | Discovery map: `commands/` domain behaviors | Opus | ✅ done | `PASS1_commands_discovery.md` |
| — | Clean slate: delete reqstool SSOT + `openspec init` | — | ✅ done | `openspec/` |
| 2 | Author content-rich OpenSpec specs — `commands/` capabilities | Opus | ✅ done | 7 specs / 37 reqs (status 9, report 6, export 5, validate 5, enrich 4, lsp 4, mcp 4); all validate strict |
| 3 | Extend OpenSpec to remaining domains (domain-by-domain, commit each) | Opus | ✅ done | 5 domains: `data-sources` (8), `ingestion` (8), `imports-and-filtering` (8), `parse-validation` (6), `lifecycle` (4) — all validate strict |
| 4 | **Flip:** derive reqstool reqs/svcs/mvrs from specs; re-annotate 21 files; thin specs; re-point CI | Opus | ⬜ todo | `docs/reqstool/*` |
| 5 | Validate: `reqstool status` green, `openspec validate --all --strict` | Sonnet | ⬜ todo | green checks |

Legend: ⬜ todo · 🟡 in progress · ✅ done · ⏸ blocked

---

## Open question — Pass 2 authoring approach (BLOCKING next step)

OpenSpec is change-oriented (`specs/` = current truth, `changes/` = deltas). Two ways to seed the
baseline:

- **A — Direct specs:** write capability specs straight into `openspec/specs/<cap>/spec.md`. Treats
  specs/ as the current-truth baseline. Lean, fits "document existing behavior." Use `/opsx:propose`
  change flow only for *future* changes.
- **B — Change ceremony:** one `/opsx:propose` change per capability (proposal/design/tasks + spec
  delta) → apply → archive → lands in specs/. Blessed flow, but tasks.md/proposal framing is awkward
  for already-built code.

Leaning **A** for the baseline. See "Decisions log" once chosen.

Other open items:
- **Capability granularity:** per CLI command (status, report, export, validate, enrich, lsp, mcp)
  vs broader behavioral groupings. Leaning per-command for `commands/`.
- **First exemplar:** author one capability fully (suggest `status` — richest behavior), validate
  the shape, then scale.

---

## Decisions log

- **2026-06-08** — Use a git worktree (`feat/openspec-reqstool-bootstrap`).
- **2026-06-08** — Pass 1 tooling: Claude-direct (repo moderate + well-documented). OpenLore not needed.
- **2026-06-08** — First-cut scope: `commands/` domain (behavior altitude).
- **2026-06-08** — **PIVOT to OpenSpec-first**: build OpenSpec as SSOT, derive reqstool in Pass 4.
  Accepted clean-slate blast radius (CI red, 21 annotations stale until flip).
- **2026-06-08** — Model split: **Opus Passes 1–4** (authoring + curated derivation), **Sonnet Pass 5**
  (validation). Switch at the Pass 4→5 boundary.
- **2026-06-08** — Pass 2 authoring: **direct specs** into `openspec/specs/<cap>/spec.md`; per-command
  granularity; `status` authored first as exemplar (validates strict).
- **2026-06-08** — Spec shape: **fine-grained** (one requirement per distinct behavior/flag) +
  **behavioral altitude** (implementation-agnostic; concrete values like exit codes pinned in
  scenarios/at the flip, not in requirement text). Applies to all command specs.
- **2026-06-08** — Source-location selection (local/git/maven/npm/pypi) is **cross-cutting**; specced
  once in the locations domain (Pass 3), not duplicated per command spec.

---

## OpenLore note

OpenLore / gen-spec (OpenSpec #634) reverse-engineers fat OpenSpec from code. Not used: repo is
moderate + well-documented, and OpenLore has pivoted to an MCP knowledge-graph runtime. Its
static-analysis layer remains a fallback if Claude-direct discovery proves too shallow.
