## 1. reqstool SSOT

- [x] 1.1 Add `MCP_0009` (MCP full-text search) to `docs/reqstool/requirements.yml` under the mcp capability block
- [x] 1.2 Add `SVC_MCP_0009` to `docs/reqstool/software_verification_cases.yml`

## 2. Index and query

- [x] 2.1 Build the FTS5 index after filtering (`build_search_index`) and rebuild it on every snapshot reload
- [x] 2.2 Rank with BM25 (ID > title > description > rationale/instructions/comment), filter by kind/URN/lifecycle
- [x] 2.3 Take `completed` for requirement hits from `compute_requirement_status`; do not re-derive it
- [x] 2.4 Fall back to LIKE matching (literal `%`/`_`) with a `note` when FTS5 is unavailable
- [x] 2.5 Reject invalid `kinds`, `lifecycle_state` and unknown `urn`; look hits up individually instead of loading all requirements
- [x] 2.6 Single-line snippets on both paths

## 3. Tool and docs

- [x] 3.1 Register the `search` MCP tool with `@Requirements("MCP_0009")`
- [x] 3.2 Document the tool in `docs/modules/ROOT/pages/mcp.adoc`, including prefix-only ID search

## 4. Verification

- [x] 4.1 Tag the tests with `@SVCs("SVC_MCP_0009")`
