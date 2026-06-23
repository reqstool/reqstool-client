## Why

The "is this requirement complete?" verdict is computed by two independent code paths that
have already drifted once: `StatisticsService` (powering `status`/`report`/`export` and the
MCP `get_status` tool) and a separate set of helpers in `common/queries/details.py`
(`_compute_meets`, `_build_automated_test_summary`) powering the MCP `get_requirement_status`
and `get_requirements_status` tools. Issue #411 patched a symptom of that drift; this change
removes the second implementation so the two can never disagree again.

## What Changes

- Extract a single per-requirement verdict computation
  (`compute_requirement_status(req, repo, *, include_post_build)`) that produces one
  `RequirementStatus` value, used by both `StatisticsService` (in its per-requirement loop) and
  the `details.py` MCP status functions. The predicate queries the repository through its scoped
  per-req getters rather than reusing bulk fetches, keeping the repository layer as the data
  boundary.
- Extract a single per-requirement serializer (`_requirement_to_dict`) called by both
  `StatisticsService.to_status_dict()` and the MCP status functions, so all status surfaces share
  one output shape by construction (not two shapes that happen to match).
- Delete the parallel predicate from `details.py` (`_compute_meets`,
  `_build_automated_test_summary`).
- Expose `include_post_build` (default `False`) on the MCP `get_requirement_status` /
  `get_requirements_status` tools, for parity with `status --with-post-tests`, so CLI and MCP
  agree in both build-only and post-build modes.
- **Forward-constraint (LSP):** no LSP completion display exists today and none is added here, but
  any future one MUST consume `compute_requirement_status` + `_requirement_to_dict` and MUST NOT
  re-derive the verdict. `MCP_0005` is worded to cover all status surfaces (CLI, MCP, LSP).
- **BREAKING (MCP output):** the MCP `get_requirement_status` and `get_requirements_status`
  tools emit the unified status shape directly (`completed`, `implementation_type`,
  `automated_tests`/`manual_tests` objects with `total` and `not_applicable`), replacing the
  old `meets_requirements` / flat `test_summary` shape. Backwards compatibility for MCP client
  output is explicitly not required.
- **BREAKING (verdict values):** routing the MCP tools through the real predicate changes
  reported verdicts for requirements with post-build-phase-only SVCs, "not applicable" cases,
  and test annotations without recorded executions — these now match the `status` command
  exactly. The MCP tools default to build-phase-only scoping to match the `status` default.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `mcp`: adds a requirement that all per-requirement status surfaces (the `status` CLI, the MCP
  status tools, and any future LSP completion display) report an identical completion verdict and
  output structure for the same input, derived from a single shared verdict computation and a
  single shared serializer, in both build-only and post-build scoping modes.

## Impact

- `src/reqstool/common/queries/details.py` — removes the duplicate predicate; status functions
  delegate to the shared computation.
- `src/reqstool/services/statistics_service.py` — per-requirement verdict logic extracted so it
  can be shared (totals accumulation stays here).
- `src/reqstool/mcp/server.py` — `get_requirement_status` / `get_requirements_status` tool
  output shape changes.
- reqstool SSOT (`docs/reqstool/requirements.yml`, `software_verification_cases.yml`) — new
  `MCP_0005` requirement and `SVC_MCP_0005`.
- MCP clients consuming `get_requirement_status` / `get_requirements_status` — output schema and
  some verdict values change (intentional).
