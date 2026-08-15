## 1. reqstool SSOT

- [x] 1.1 Add `MCP_0006` (snapshot freshness), `MCP_0007` (reload failure reporting) and `MCP_0008` (snapshot provenance and missing artifact reporting) to `docs/reqstool/requirements.yml` under the mcp capability block
- [x] 1.2 Add `SVC_MCP_0006`, `SVC_MCP_0007` and `SVC_MCP_0008` to `docs/reqstool/software_verification_cases.yml`
- [x] 1.3 Run `openspec validate mcp-snapshot-freshness --type change --strict` and confirm it passes

## 2. Fingerprint the parsed inputs

- [x] 2.1 Add `SnapshotFingerprint` (`FileStamp`, `GlobSpec`) with `stale_reasons()`, `is_stale()`, `restamped()` and `warnings()`
- [x] 2.2 Capture it per parsed source in `CombinedRawDatasetsGenerator.__parse_source`, for `LocalLocation` only, recording paths under the real project directory rather than the temp symlink tree
- [x] 2.3 Stamp the four data YAMLs and `reqstool_config.yml` whether or not they exist, so a file the build generates later registers as a change
- [x] 2.4 Record each `test_results` pattern with the concrete files it matched — `__parse_source_other` returns them instead of discarding them
- [x] 2.5 Aggregate onto `CombinedRawDataset`, mirroring `urn_source_paths`

## 3. Reload the session when its inputs change

- [x] 3.1 Track `fingerprint`, `built_at` and `initial_urn` on `ProjectSession`
- [x] 3.2 Add `ensure_fresh()` — rebuild only when the fingerprint no longer matches disk; raise `SnapshotReloadError` when the session cannot serve a snapshot that matches
- [x] 3.3 Re-stamp the known inputs after a failed build, so a tree that does not parse is not re-parsed on every request
- [x] 3.4 Guard build/close/ensure_fresh with a lock — a reload replaces the database underneath request handlers
- [x] 3.5 Leave the LSP path alone: it rebuilds from client file-change notifications and does not call `ensure_fresh()`

## 4. MCP server

- [x] 4.1 Resolve the repository per tool call via a `_repo()` helper instead of binding it at startup — reloading is invisible to the tools otherwise
- [x] 4.2 Add a `refresh` tool that reloads unconditionally and reports the resulting snapshot
- [x] 4.3 Add a `snapshot` field to `get_status` with `built_at`, `reload`, `tracked_files` and `warnings`
- [x] 4.4 Report `test_results` patterns matching no files as warnings; report a missing annotations file only for the served URN, since imported sources are not expected to carry annotations
- [x] 4.5 Add `@Requirements` annotations for `MCP_0006`, `MCP_0007` and `MCP_0008`

## 5. Tests

- [x] 5.1 Unit-test the fingerprint: modified, removed and later-created files; new and rewritten test results; zero-match patterns; `restamped()`
- [x] 5.2 Unit-test `ProjectSession.ensure_fresh()` against a writable copy of a fixture: unchanged tree is not rebuilt, changed annotations and test results are picked up, a broken tree errors and recovers once fixed
- [x] 5.3 Unit-test the MCP tools driven while the project changes underneath a live server
- [x] 5.4 Integration-test a real spawned server (`tests/integration/reqstool/mcp/test_mcp_reload_integration.py`) against a writable project copy: annotations added after startup are served, `refresh` reloads, a project that no longer parses errors rather than answering stale
- [x] 5.5 Add `@SVCs` annotations to the verifying tests

## 6. Documentation

- [x] 6.1 Document the `refresh` tool and the `snapshot` field in `docs/modules/ROOT/pages/mcp.adoc`
- [x] 6.2 Add a "Snapshot Freshness" section covering what is watched, what happens when a reload fails, and that remote sources are not watched

## 7. Verification

- [x] 7.1 Run `hatch run dev:pytest --cov=reqstool` (unit and integration) and `hatch run dev:flake8`
- [x] 7.2 Run the CLAUDE.md regression smoke diffs against `main` — CLI output must be byte-identical
- [x] 7.3 Run `reqstool status local -p docs/reqstool` and confirm the new SVCs are covered
- [x] 7.4 Run `openspec validate --all --strict`
