## 1. reqstool SSOT

- [ ] 1.1 Add `MCP_0005` (per-requirement status tool verdict/shape consistency) to `docs/reqstool/requirements.yml` under the mcp capability block
- [ ] 1.2 Add `SVC_MCP_0005` (verifies `get_requirement_status`/`get_requirements_status` agree with `status`) to `docs/reqstool/software_verification_cases.yml`
- [ ] 1.3 Run `openspec validate consolidate-requirement-verdict --type change --strict` and confirm it passes

## 2. Extract the shared verdict predicate

- [ ] 2.1 Add a freestanding `compute_requirement_status(req, repo, *, include_post_build) -> RequirementStatus` that encapsulates the per-requirement implementation/automated/manual verdict logic currently in `StatisticsService._calculate_requirement_stats`
- [ ] 2.2 Refactor `StatisticsService._calculate_requirement_stats` to call the extracted predicate, keeping `_update_requirement_totals` (totals accumulation) in `StatisticsService`
- [ ] 2.3 Verify `status`/`report`/`export` output is unchanged (statistics unit tests pass; CLAUDE.md regression smoke diffs are byte-identical)

## 3. Route MCP status tools through the predicate

- [ ] 3.1 Rewrite `get_requirement_status` / `get_requirements_status_all` in `details.py` to call `compute_requirement_status` with `include_post_build=False`
- [ ] 3.2 Serialize the resulting `RequirementStatus` to the unified shape (`completed`, `implementation_type`, `automated_tests`/`manual_tests` with `total` and `not_applicable`), matching `to_status_dict()`'s per-requirement shape
- [ ] 3.3 Delete `_compute_meets` and `_build_automated_test_summary` from `details.py`
- [ ] 3.4 Add `@Requirements("MCP_0005")` to the implementing function(s) for the consolidated MCP status path

## 4. Tests

- [ ] 4.1 Add a test asserting `get_requirement_status` / `get_requirements_status` agree with `StatisticsService` per requirement on the `test_standard/baseline/ms-001` fixture, covering the previously divergent `REQ_ext002_300`
- [ ] 4.2 Add `@SVCs("SVC_MCP_0005")` to the test method from 4.1
- [ ] 4.3 Update any existing tests asserting the old `meets_requirements` / flat `test_summary` MCP shape to the new shape

## 5. Verification

- [ ] 5.1 Run `hatch run dev:pytest --cov=reqstool` and `hatch run dev:flake8`
- [ ] 5.2 Run `reqstool status local -p docs/reqstool` (via `hatch run python src/reqstool/command.py`) and confirm 72/72 complete with `SVC_MCP_0005` covered
- [ ] 5.3 Run `openspec validate --all --strict`
