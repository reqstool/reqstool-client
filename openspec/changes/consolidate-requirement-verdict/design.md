## Context

Two code paths compute whether a requirement is "complete":

- `StatisticsService._calculate_requirement_stats` (`src/reqstool/services/statistics_service.py`)
  produces a `RequirementStatus` (with `TestStats` for automated and manual evidence) and is the
  authoritative path behind `status`, `report`, `export`, and the MCP `get_status` tool.
- `common/queries/details.py` (`_compute_meets` + `_build_automated_test_summary`) re-derives the
  same verdict via a different traversal and powers the MCP `get_requirement_status` and
  `get_requirements_status` tools.

The two are not equivalent, even after #411's patch:

| Aspect | `StatisticsService` | `details.py` |
| --- | --- | --- |
| SVC phase scoping | build-phase only unless `include_post_build` | all SVCs, no phase filter |
| "applies at all" gate | `not_applicable` when no SVC expects automated/MVR evidence | always requires all-passing |
| automated test source | walks test annotations, matches by FQN, marks MISSING per annotation | reads `get_test_results_for_svc` directly |
| no-qualifying-SVC | `completed=False` unless some SVC expects evidence | only requires a non-empty SVC list |

`get_status` already uses `StatisticsService` directly, so the inconsistency is isolated to the
two per-requirement/scoped MCP tools. The constraint that matters: there is no backwards-compat
requirement on MCP tool output, so the fix can change both the schema and the verdict values.

The goal is stronger than "make the two agree": there must be **one** place that computes the
"complete" verdict and **one** place that serializes it, so that the CLI (`status`), the MCP
tools, and any future LSP completion display all return identical results for identical input.

## Goals / Non-Goals

**Goals:**
- One per-requirement verdict computation, called by both `StatisticsService` and `details.py`.
- One per-requirement serializer, called by both `StatisticsService.to_status_dict()` and the MCP
  status tools — same verdict *and* same output shape, not two shapes that happen to match.
- `status` (CLI), the MCP status tools, and any future LSP completion display report the same
  `completed` verdict and output structure for the same input, in **both** build-only and
  `--with-post-tests` (post-build) modes.
- Delete `_compute_meets` and `_build_automated_test_summary`.

**Non-Goals:**
- Changing the `status`, `report`, or `export` command behavior or output.
- Changing `get_status` (already unified).
- Adding new MCP tools or changing transports / dataset resolution.
- Implementing an LSP completion display now (none exists yet) — see the forward-constraint below.

## Decisions

### Extract a per-requirement predicate that queries the repository directly

Introduce a single function `compute_requirement_status(req, repo, *, include_post_build) ->
RequirementStatus` that computes the verdict for one requirement by **querying the repository**
through its scoped, index-backed per-requirement getters (`get_svcs_for_req`,
`get_annotations_impls_for_req`, `get_annotations_tests_for_svc`, `get_test_results_for_svc`,
`get_effective_mvr_for_svc`). `StatisticsService._calculate_requirement_stats` calls it inside its
loop; `details.py` calls it per id. `StatisticsService` keeps owning global aggregation
(`_calculate_global_totals`) and totals accumulation (`_update_requirement_totals`), fed by the
`RequirementStatus` the predicate returns.

- **Why query the repo rather than thread a pre-fetched data bundle**: the repository layer exists
  precisely so business logic asks the database for what it needs. Passing the four bulk tables
  (`get_all_svcs`, `get_annotations_impls`, `get_annotations_tests`, `get_automated_test_results`)
  into the predicate would leak the repo's job onto every caller and couple the signature to
  `StatisticsService`'s fetch strategy.
- **Why this is not a perf regression**: the per-req getters are backed by primary keys and FK
  indexes (`schema.py`) on an in-memory SQLite database; total work across a `status` run is
  comparable to today's four bulk `SELECT *` calls. If query volume ever matters at scale, the fix
  is repository-level caching — a separate concern, not a reason to complicate this signature.
- **Trade-off**: requires untangling `_calculate_requirement_stats` from
  `_update_requirement_totals`, which today run in the same pass.

### One shared per-requirement serializer

Extract `_requirement_to_dict(status: RequirementStatus) -> dict` (the per-requirement body of
`StatisticsService.to_status_dict()`, producing `completed`, `implementation_type`,
`automated_tests`/`manual_tests` with `total` and `not_applicable`). `to_status_dict()` calls it,
and the `details.py` MCP status functions call it. No mapping back to the old `meets_requirements`
/ flat `test_summary` dict.

- **Why**: a unified verdict that is serialized two different ways still diverges from the
  consumer's point of view — same value, different JSON — which is how the original drift began.
  Sharing the serializer keeps all status surfaces on one schema by construction, not by
  coincidence. Backwards compatibility is not required (project decision), so preserving the legacy
  dict would only perpetuate a second shape.

### Expose the post-build scoping flag on every status surface

The predicate's `include_post_build` flag is plumbed through to the MCP tools as an optional
parameter (default `False`, matching the `status` default) so the MCP tools have parity with
`status --with-post-tests`. The same parameter is the contract for any future LSP completion
display. This closes the last verdict-divergence gap: CLI = MCP = LSP in **both** modes, not just
the default.

### LSP is a forward-constraint, not implemented here

There is no LSP completion display today (no verdict code in `src/reqstool/lsp/`). This change does
not add one. It does bind the future: when LSP gains a completion display it MUST call
`compute_requirement_status` + `_requirement_to_dict` (with the same `include_post_build`
contract) and MUST NOT re-derive the verdict. `MCP_0005` is worded to cover all status surfaces so
the third consumer cannot silently fork later. This mirrors the convention note in `CLAUDE.md`.

## Risks / Trade-offs

- **Untangling totals from per-req stats introduces regressions in `status`/`report`/`export`** →
  Mitigation: keep totals accumulation in `StatisticsService`; the extracted predicate returns the
  same `RequirementStatus` the loop already builds, so totals read identical inputs. Guard with the
  existing statistics unit tests and the CLAUDE.md regression smoke diffs (must be byte-identical for
  `status`/`report`).
- **MCP verdict/shape change surprises consumers** → Mitigation: documented as intentional BREAKING
  in the proposal; the new values are the correct, `status`-consistent ones.
- **Hidden behavioral difference between the two old paths becomes visible** → Mitigation: add MCP
  tests asserting `get_requirement_status` / `get_requirements_status` agree with
  `StatisticsService` on the same fixtures (including the `REQ_ext002_300` divergence case).
