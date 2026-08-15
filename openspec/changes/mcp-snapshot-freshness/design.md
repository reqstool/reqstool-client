# Design

## Why not re-parse per request

Issue #437 suggests re-reading sources and artifacts on every request. That is correct but
expensive in the wrong place: a rebuild walks the whole import chain, including remote imports,
which means network fetches for git/maven/pypi sources on every tool call.

Stat-then-rebuild gives the same freshness guarantee for local sources at the cost of a few dozen
`stat()` calls and one `rglob` per configured test-result pattern, and remote imports are
version-pinned anyway. The check runs unconditionally per request — no debounce interval — because
a debounce window is exactly the "answered from just before the build" case this change exists to
eliminate.

## What is fingerprinted

Per parsed source, when its location is local:

| Tracked | Why |
|---|---|
| `requirements.yml`, `software_verification_cases.yml`, `manual_verification_results.yml`, `annotations.yml` | The parsed inputs. Stamped whether or not they exist, so a file the build generates later registers as a change. |
| `reqstool_config.yml` | Decides which files and patterns are read at all. |
| each `test_results` pattern + the files it matched | Test results are resolved from globs; a new JUnit XML under a matched pattern has to count. Each matched file is stamped, so a rewritten report counts too. |

Stamps compare `(exists, st_mtime_ns, st_size)`. Content hashing was not used: it buys protection
against a rewrite that preserves both mtime and size, which no build produces, at the cost of
reading every file on every request.

Paths are recorded under the **real project directory**, not the temp tree. A local location is
materialized as a symlink into a `TemporaryDirectory` owned by the generator, and that directory is
gone by the time staleness is checked.

## Failure handling

`build()` failing leaves the session not ready and the database closed — deliberately, since the
alternative is serving data known to be superseded. Two details make that survivable:

- The failed build re-stamps the previous fingerprint against current disk. A tree that does not
  parse is therefore parsed once, not once per request, and the next edit makes it stale again.
- `ensure_fresh()` distinguishes the two states in its message: *sources changed but reloading them
  failed* (this call triggered the rebuild) versus *project is not loaded* (an earlier reload failed
  and nothing has changed since).

## Concurrency

`ensure_fresh()` can replace the database underneath a request handler, so `ProjectSession` guards
build/close/ensure_fresh with an `RLock`. MCP tools are async and run on the event loop thread,
which is also the thread the SQLite connection is created on, so the rebuild happens on the
connection's own thread — a rebuild blocks the loop for its duration, as the startup build already
does.

## Where the verdict comes from

`get_status` continues to derive every number from `StatisticsService`. The `snapshot` field
describes the *inputs*, never the verdict, so this change adds no second opinion about whether a
requirement is complete (see MCP_0005 and CLAUDE.md).
