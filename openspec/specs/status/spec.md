# status Specification

## Purpose

The `status` command reports the implementation and verification state of every requirement in a
reqstool dataset, computes an overall PASS/FAIL verdict, and exposes that verdict to CI via its exit
code. It is the primary command teams run in pipelines to gate a build on requirement coverage.

A requirement is **complete** when it is implemented (or declared non-code) AND all of its automated
tests pass AND all of its manual verification results pass. Anything else is **incomplete**.

## Requirements

### Requirement: Requirement status computation

The system SHALL compute, for every requirement in the dataset, its implementation state, automated
test outcome, and manual verification outcome, and SHALL classify each requirement as complete or
incomplete on that basis.

#### Scenario: Requirement fully implemented and verified

- **WHEN** a requirement has at least one implementing annotation, all linked automated tests pass,
  and all manual verification results pass
- **THEN** the system classifies the requirement as complete

#### Scenario: Requirement missing implementation

- **WHEN** an in-code requirement has no implementing annotation
- **THEN** the system classifies the requirement as incomplete with reason "not implemented"

#### Scenario: Requirement with failing automated test

- **WHEN** a requirement's linked automated test reports a failure
- **THEN** the system classifies the requirement as incomplete and reports the passed/total test counts

#### Scenario: Non-code requirement

- **WHEN** a requirement declares a non-code implementation type (not-applicable, configuration,
  platform, or framework)
- **THEN** the system does not require an implementing annotation and shows the declared type in place
  of an implementation count

### Requirement: Completion verdict

The system SHALL derive an overall verdict from the number of incomplete requirements, reporting PASS
when no requirements are incomplete and FAIL otherwise.

#### Scenario: All requirements complete

- **WHEN** every requirement in the dataset is complete
- **THEN** the system reports the verdict PASS

#### Scenario: One or more requirements incomplete

- **WHEN** at least one requirement is incomplete
- **THEN** the system reports the verdict FAIL together with the complete/total and incomplete counts

### Requirement: Console verbosity levels

The system SHALL provide four console verbosity levels — compact, normal, verbose, and
extra-verbose — that present increasing detail, defaulting to normal.

#### Scenario: Compact output

- **WHEN** the user selects compact verbosity
- **THEN** the system emits a single summary line with total, complete, incomplete counts and the verdict

#### Scenario: Extra-verbose output

- **WHEN** the user selects extra-verbose verbosity
- **THEN** the system drills down each incomplete requirement to show its implementing annotations, its
  SVCs, and the underlying test results or manual verification results

### Requirement: Incomplete-only filtering

The system SHALL support restricting console output to only incomplete requirements.

#### Scenario: Hiding complete requirements

- **WHEN** the user requests incomplete-only output
- **THEN** the system omits the complete section and lists only incomplete requirements

### Requirement: JSON output format

The system SHALL be able to emit status as a structured JSON document as an alternative to console
output, and SHALL ignore console verbosity when JSON is selected.

#### Scenario: JSON requested

- **WHEN** the user selects JSON output
- **THEN** the system emits a machine-readable status document for all requirements

#### Scenario: Verbosity ignored under JSON

- **WHEN** the user selects JSON output together with a non-default verbosity
- **THEN** the system warns that verbosity has no effect and proceeds with JSON output

### Requirement: Requirement and SVC filtering

The system SHALL allow the status output to be filtered to a specified set of requirement IDs or SVC
IDs.

#### Scenario: Filtering to specific requirement IDs

- **WHEN** the user supplies one or more requirement IDs to a JSON status run
- **THEN** the system restricts the emitted status document to the requirements in scope of those IDs

### Requirement: CI gating exit code

The system SHALL, when explicitly asked to enforce coverage, exit with a dedicated non-zero code if
any requirement is unmet, and otherwise exit zero.

#### Scenario: Gating enabled with unmet requirements

- **WHEN** the user enables all-requirements-met enforcement and at least one requirement is incomplete
- **THEN** the system exits with the all-requirements-not-implemented exit code

#### Scenario: Gating disabled

- **WHEN** the user does not enable enforcement
- **THEN** the system exits zero regardless of incomplete requirements

### Requirement: Post-build test gating

The system SHALL accept one or more post-build JUnit XML result files and incorporate their outcomes
into the status computation.

#### Scenario: Post-build results supplied

- **WHEN** the user supplies one or more post-build test result files
- **THEN** the system injects those results into the dataset and activates post-build gating in the
  computed status

#### Scenario: Post-build file missing

- **WHEN** a supplied post-build test result file does not exist
- **THEN** the system reports the missing file and does not produce a status

### Requirement: Output destination

The system SHALL write status output to a file when a path is given and to standard output otherwise.

#### Scenario: Output to file

- **WHEN** the user supplies an output file path
- **THEN** the system writes the status to that file, creating parent directories as needed

#### Scenario: Default to stdout

- **WHEN** the user supplies no output path
- **THEN** the system writes the status to standard output
