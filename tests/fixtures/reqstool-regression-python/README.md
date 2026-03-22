# reqstool-regression-python (fixture)

Self-contained Python fake-project fixture for LSP integration testing.
When the real `reqstool-regression-python` repo is created, this directory becomes a git submodule.

## Enum Coverage Matrix

### Requirements

| ID | Title | Significance | Lifecycle | Categories | Implementation |
|----|-------|-------------|-----------|------------|---------------|
| `REQ_PASS` | Greeting message | **shall** | effective *(default)* | functional-suitability | in-code |
| `REQ_MANUAL_FAIL` | Calculate total | **should** | effective | performance-efficiency, reliability | in-code |
| `REQ_NOT_IMPLEMENTED` | Export report | **may** | **draft** | compatibility, interaction-capability | **N/A** |
| `REQ_FAILING_TEST` | Email validation | shall | effective | security | in-code |
| `REQ_SKIPPED_TEST` | SMS notification | may | **deprecated** | maintainability | in-code |
| `REQ_MISSING_TEST` | Audit logging | shall | effective | safety, flexibility | in-code |
| `REQ_OBSOLETE` | Legacy greeting | should | **obsolete** | interaction-capability | in-code |

**Coverage**: all 3 significance, all 4 lifecycle, all 9 categories, both implementation types.

### SVCs

| ID | Req IDs | Verification | Lifecycle | Test outcome |
|----|---------|-------------|-----------|-------------|
| `SVC_010` | REQ_PASS | **automated-test** | effective | PASS (unit + integration) |
| `SVC_020` | REQ_MANUAL_FAIL | automated-test | effective | PASS |
| `SVC_021` | REQ_PASS | **manual-test** | effective | MVR pass |
| `SVC_022` | REQ_MANUAL_FAIL | manual-test | effective | MVR fail |
| `SVC_030` | REQ_NOT_IMPLEMENTED | **review** | effective | *(N/A)* |
| `SVC_040` | REQ_FAILING_TEST | automated-test | effective | FAIL |
| `SVC_050` | REQ_SKIPPED_TEST | **platform** | **deprecated** | SKIPPED |
| `SVC_060` | REQ_MISSING_TEST | automated-test | effective | NO TEST |
| `SVC_070` | REQ_OBSOLETE | **other** | **obsolete** | *(N/A)* |

**Coverage**: all 5 verification types, all test outcomes.

### MVRs

| ID | SVC IDs | Pass | Comment |
|----|---------|------|---------|
| `MVR_201` | SVC_021 | true | Greeting message correctly displayed |
| `MVR_202` | SVC_022 | false | Rounding error: 9.99 instead of 10.00 |

## Structure

```
reqstool-regression-python/
  requirements.yml
  software_verification_cases.yml
  manual_verification_results.yml
  annotations.yml
  reqstool_config.yml
  test_results/
    surefire/TEST-py_demo.test_svcs.xml
    failsafe/TEST-py_demo.test_svcs_it.xml
  src/
    requirements_example.py
    test_svcs.py
```
