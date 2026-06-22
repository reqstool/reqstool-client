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

## Goals / Non-Goals

**Goals:**
- One per-requirement verdict computation, called by both `StatisticsService` and `details.py`.
- MCP `get_requirement_status` / `get_requirements_status` report the same `completed` verdict and
  the same output structure as the `status` command for the same input.
- Delete `_compute_meets` and `_build_automated_test_summary`.

**Non-Goals:**
- Changing the `status`, `report`, or `export` command behavior or output.
- Changing `get_status` (already unified).
- Adding new MCP tools or changing transports / dataset resolution.

## Decisions

### Extract a freestanding per-requirement predicate (not a wrapper)

Introduce a single function that computes a `RequirementStatus` for one requirement given the
repository and a `include_post_build` flag. `StatisticsService._calculate_requirement_stats`
calls it inside its loop and keeps owning totals accumulation; `details.py` calls it per id.

- **Why over a thin wrapper** (have `details.py` build a `StatisticsService` and read
  `.requirement_statistics[urn_id]`): a wrapper makes the two agree but keeps two algorithms;
  it also couples the MCP query layer to `StatisticsService` internals. Extracting the predicate
  yields one literal source of truth and cleanly separates "verdict for one requirement" from
  "aggregate totals across all requirements."
- **Trade-off**: requires untangling `_calculate_requirement_stats` from
  `_update_requirement_totals`, which today run in the same pass. This is the bulk of the work.

### Emit the unified shape directly from the MCP tools

The two `details.py` status functions serialize the `RequirementStatus` the same way
`StatisticsService.to_status_dict()` does per requirement (`completed`, `implementation_type`,
`automated_tests`/`manual_tests` with `total` and `not_applicable`). No mapping back to the old
`meets_requirements` / flat `test_summary` dict.

- **Why**: backwards compatibility is not required (project decision), so preserving the legacy
  dict would only perpetuate a second shape. A shared per-requirement serializer keeps all status
  tools on one schema.

### Default MCP tools to build-phase-only scoping

To match the `status` command default, the predicate is invoked with `include_post_build=False`
from the MCP tools. Optionally expose the flag as a tool parameter for parity with
`status --with-post-tests` (can be deferred).

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
