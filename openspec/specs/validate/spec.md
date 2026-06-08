# validate Specification

## Purpose

The `validate` command checks a reqstool dataset for specification completeness and referential
integrity: that every requirement is covered by at least one SVC, that every manual SVC has a
recorded manual verification result, and that all cross-references resolve. It is intended as a
fast authoring-time check, distinct from the status command's coverage gating.

## Requirements

### Requirement: SVC coverage check

The system SHALL report every requirement that has no software verification case defined.

#### Scenario: Requirement without an SVC

- **WHEN** a requirement has no SVC referencing it
- **THEN** the system reports that requirement as a coverage gap

### Requirement: Manual verification coverage check

The system SHALL report every SVC that expects a manual verification result but has none recorded.

#### Scenario: Manual SVC without an MVR

- **WHEN** an SVC requires manual verification and no manual verification result references it
- **THEN** the system reports that SVC as a coverage gap

### Requirement: Referential integrity check

The system SHALL report referential-integrity errors where an SVC, MVR, or annotation references a
non-existent entity, and SHALL treat such errors as fatal.

#### Scenario: Broken reference

- **WHEN** an SVC, MVR, or annotation references an entity that does not exist
- **THEN** the system reports a referential error and fails

### Requirement: Strict mode

The system SHALL treat coverage gaps as warnings by default and as errors when strict mode is
enabled.

#### Scenario: Coverage gap in default mode

- **WHEN** only coverage gaps are present and strict mode is disabled
- **THEN** the system reports warnings and succeeds

#### Scenario: Coverage gap in strict mode

- **WHEN** coverage gaps are present and strict mode is enabled
- **THEN** the system reports errors and fails

### Requirement: Validation summary

The system SHALL summarize the outcome with counts of errors and warnings and an overall
pass/fail result, and SHALL signal failure through its exit code.

#### Scenario: Clean dataset

- **WHEN** no referential errors and no coverage gaps are found
- **THEN** the system reports that all checks passed and exits successfully
