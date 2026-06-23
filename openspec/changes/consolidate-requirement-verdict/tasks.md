## 1. reqstool SSOT

- [x] 1.1 Add `MCP_0005` (per-requirement status tool verdict/shape consistency) to `docs/reqstool/requirements.yml` under the mcp capability block
- [x] 1.2 Add `SVC_MCP_0005` (verifies `get_requirement_status`/`get_requirements_status` agree with `status`) to `docs/reqstool/software_verification_cases.yml`
- [x] 1.3 Run `openspec validate consolidate-requirement-verdict --type change --strict` and confirm it passes

## 2. Extract the shared verdict predicate

- [x] 2.1 Add `compute_requirement_status(req, repo, *, include_post_build) -> RequirementStatus` that encapsulates the per-requirement implementation/automated/manual verdict logic currently in `StatisticsService._calculate_requirement_stats`. It MUST obtain its data by querying the repository through the scoped per-req getters (`get_svcs_for_req`, `get_annotations_impls_for_req`, `get_annotations_tests_for_svc`, `get_test_results_for_svc`, `get_effective_mvr_for_svc`) — do NOT thread pre-fetched bulk tables through the signature
- [x] 2.2 Refactor `StatisticsService._calculate_requirement_stats` to call the extracted predicate, keeping `_calculate_global_totals` and `_update_requirement_totals` (global aggregation + totals accumulation) in `StatisticsService`
- [x] 2.3 Verify `status`/`report`/`export` output is unchanged (statistics unit tests pass; CLAUDE.md regression smoke diffs are byte-identical)

## 3. Share the serializer and route MCP status tools through the predicate

- [x] 3.1 Extract `_requirement_to_dict(status: RequirementStatus) -> dict` (the per-requirement body of `to_status_dict()`: `completed`, `implementation_type`, `automated_tests`/`manual_tests` with `total` and `not_applicable`) and make `to_status_dict()` call it
- [x] 3.2 Rewrite `get_requirement_status` / `get_requirements_status_all` in `details.py` to call `compute_requirement_status` and serialize via the shared `_requirement_to_dict` — same code, not a re-implemented matching shape
- [x] 3.3 Expose `include_post_build` (default `False`) as an optional parameter on the MCP `get_requirement_status` / `get_requirements_status` tools, for parity with `status --with-post-tests`
- [x] 3.4 Delete `_compute_meets` and `_build_automated_test_summary` from `details.py`
- [x] 3.5 Add `@Requirements("MCP_0005")` to the implementing function(s) for the consolidated MCP status path

## 4. Tests

- [x] 4.1 Add a test asserting `get_requirement_status` / `get_requirements_status` agree with `StatisticsService` per requirement on the `test_standard/baseline/ms-001` fixture, covering the previously divergent `REQ_ext002_300`
- [x] 4.2 Assert agreement in **both** modes: `include_post_build=False` (default) and `True` (parity with `status --with-post-tests`)
- [x] 4.3 Add `@SVCs("SVC_MCP_0005")` to the test method from 4.1
- [x] 4.4 Update any existing tests asserting the old `meets_requirements` / flat `test_summary` MCP shape to the new shape

## 5. Verification

- [x] 5.1 Run `hatch run dev:pytest --cov=reqstool` and `hatch run dev:flake8`
- [x] 5.2 Run `reqstool status local -p docs/reqstool` (via `hatch run python src/reqstool/command.py`) and confirm all requirements complete with `SVC_MCP_0005` covered
- [x] 5.3 Run `openspec validate --all --strict`
