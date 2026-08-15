## Why

`reqstool mcp` parses the project once at startup and then serves that snapshot for as long as
the process lives. AI harnesses spawn the server and keep it up for days, while builds regenerate
`annotations.yml` and JUnit XML underneath it. Issue #437 reports the consequence: a server
spawned days earlier answered `get_status` with 14 requirements, 0 implementations, 0 tests, while
the CLI against the same tree reported 55/55 complete. The stale answer is well-formed, so neither
an agent nor a human can tell it apart from a real result.

Two things cause it. The server binds the repository into its tool closures at startup, so nothing
short of a restart can change what the tools read. And nothing records which files were parsed, so
there is no way to notice that the tree moved on — in particular "the `test_results` pattern
matched no files" is indistinguishable from "this project has no tests".

## What Changes

- Capture a **fingerprint** of the local input files each parse read: the four data YAMLs plus
  `reqstool_config.yml`, stamped whether or not they exist, and each `test_results` glob pattern
  together with the concrete files it matched. Files absent at parse time are tracked deliberately
  — an `annotations.yml` the build has yet to generate is the common staleness trigger. Remote
  sources (git/maven/npm/pypi) are version-pinned downloads materialized into a temp directory that
  is removed after parsing, so they are not fingerprinted and never go stale.
- Add `ProjectSession.ensure_fresh()`: re-stat the fingerprint, rebuild only if it no longer
  matches. The LSP keeps calling `rebuild()` directly from its client file-change notifications;
  MCP has no such channel, which is why it checks per request.
- **MCP tools resolve the repository per call** instead of closing over it at startup. Without
  this, reloading would be invisible to the tools.
- **A failed reload is an error, not a fallback.** If the inputs changed but the new state does not
  parse, tools raise `SnapshotReloadError` rather than answering from the superseded snapshot. The
  failed build re-stamps the inputs it knew about, so a broken tree is not re-parsed on every
  request until it is fixed.
- Add a `refresh` tool that reloads unconditionally, and a `snapshot` field on `get_status`
  reporting `built_at`, `tracked_files`, and `warnings` — where a `test_results` pattern matching
  no files is reported explicitly instead of being counted as zero tests.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `mcp`: adds requirements that the server answers from a snapshot reflecting the current state of
  the served project's local files (reloading automatically and on request), that a reload which
  fails is reported as an error rather than answered from the superseded snapshot, and that the
  snapshot's parse time and any test-result patterns matching no files are reported.

## Impact

- `src/reqstool/common/snapshot_fingerprint.py` — new; the fingerprint and its staleness check.
- `src/reqstool/model_generators/combined_raw_datasets_generator.py` — records the fingerprint per
  parsed source; `__parse_source_other` now also returns the test-result files each pattern matched.
- `src/reqstool/models/raw_datasets.py` — `fingerprint` on `RawDataset` and `CombinedRawDataset`.
- `src/reqstool/common/project_session.py` — fingerprint, `built_at`, `initial_urn`,
  `ensure_fresh()`, and a lock around rebuilds.
- `src/reqstool/mcp/server.py` — per-call repository resolution, `refresh` tool, `snapshot` field.
- MCP clients — `get_status` gains a `snapshot` field (additive); tool calls can now fail with a
  load error where they previously returned stale numbers (intentional).
- Not changed: the CLI, which parses per invocation and was never affected.

## Non-goals

- A `verify` tool with CLI-gate semantics (issue #437, point 3). It belongs with the `status`/
  `export` redesign in #311 and must derive from the shared verdict computation (MCP_0005), so it
  is deliberately left out of this change.
- Watching remote sources. A `GitLocation` pinned to a moving branch ref is technically mutable;
  `refresh` covers it.
