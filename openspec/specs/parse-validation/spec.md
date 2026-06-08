# parse-validation Specification

## Purpose

While building the dataset, reqstool checks the input for structural and referential problems and
surfaces them to the user. These checks run on every command (they are part of building the model),
and are distinct from the `validate` command, which performs an explicit spec-completeness review.
Structural problems and a missing required file are errors; duplicate identifiers and references to
unknown identifiers are warnings.

## Requirements

### Requirement: Schema validation

The system SHALL validate each input file against its JSON schema before parsing and report a
validation error when a file does not conform.

#### Scenario: Non-conforming file

- **WHEN** an input file does not conform to its JSON schema
- **THEN** the system reports a schema validation error and does not parse the file as valid

### Requirement: Missing requirements file

The system SHALL fail with a clear error when no `requirements.yml` file is found at the provided
content root.

#### Scenario: Requirements file absent

- **WHEN** the provided content root contains no `requirements.yml`
- **THEN** the system reports that the required file is missing and exits with an error

### Requirement: Duplicate requirement identifiers

The system SHALL warn when duplicate requirement identifiers are detected during parsing.

#### Scenario: Two requirements share an ID

- **WHEN** two requirements are parsed with the same identifier
- **THEN** the system logs a warning identifying the duplicate

### Requirement: Duplicate SVC identifiers

The system SHALL warn when duplicate SVC identifiers are detected during parsing.

#### Scenario: Two SVCs share an ID

- **WHEN** two SVCs are parsed with the same identifier
- **THEN** the system logs a warning identifying the duplicate

### Requirement: Dangling requirement references

The system SHALL warn when a reference to a non-existent requirement identifier is detected during
parsing.

#### Scenario: Reference to unknown requirement

- **WHEN** an SVC or annotation references a requirement identifier that does not exist
- **THEN** the system logs a warning identifying the unresolved reference

### Requirement: Dangling SVC references

The system SHALL warn when a reference to a non-existent SVC identifier is detected during parsing.

#### Scenario: Reference to unknown SVC

- **WHEN** a manual verification result or annotation references an SVC identifier that does not exist
- **THEN** the system logs a warning identifying the unresolved reference
