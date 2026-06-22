## Why

The "is this requirement complete?" verdict is computed by two independent code paths that
have already drifted once: `StatisticsService` (powering `status`/`report`/`export` and the
MCP `get_status` tool) and a separate set of helpers in `common/queries/details.py`
(`_compute_meets`, `_build_automated_test_summary`) powering the MCP `get_requirement_status`
and `get_requirements_status` tools. Issue #411 patched a symptom of that drift; this change
removes the second implementation so the two can never disagree again.

## What Changes

- Extract a single per-requirement verdict computation that produces one `RequirementStatus`
  value, used by both `StatisticsService` (in its per-requirement loop) and the `details.py`
  MCP status functions.
- Delete the parallel predicate from `details.py` (`_compute_meets`,
  `_build_automated_test_summary`).
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
- `mcp`: adds a requirement that the per-requirement MCP status tools report a completion
  verdict and output structure identical to the `status` command, derived from a single shared
  verdict computation.

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
