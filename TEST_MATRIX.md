# Test Matrix

After making changes to the `export` command, run these scenarios and verify the output.

Test data path: `tests/resources/test_data/data/local/test_standard/baseline/ms-001`

## generate command

| # | Command | Expected |
|---|---------|----------|
| 1 | `reqstool export local -p <path>` | Full JSON output, all reqs/SVCs/MVRs |
| 2 | `reqstool export local -p <path> --req-ids REQ_010` | Only REQ_010 + related SVCs (SVC_010, SVC_021) |
| 3 | `reqstool export local -p <path> --req-ids REQ_010 REQ_020` | Both reqs + their SVCs |
| 4 | `reqstool export local -p <path> --svc-ids SVC_010` | Only SVC_010 + related reqs/MVRs |
| 5 | `reqstool export local -p <path> --svc-ids SVC_010 SVC_020` | Both SVCs |
| 6 | `reqstool export local -p <path> --req-ids REQ_010 --svc-ids SVC_022` | Union of both filters |
| 7 | `reqstool export local -p <path> --req-ids REQ_NONEXISTENT` | Warning on stderr, empty requirements |
| 8 | `reqstool generate-json local -p <path>` | Deprecation warning on stderr, full JSON output |
| 9 | `reqstool export --format json local -p <path>` | Same as #1 |
| 10 | `reqstool export local -p <path> --requirement-ids REQ_010` | Same as #2 (alias) |
