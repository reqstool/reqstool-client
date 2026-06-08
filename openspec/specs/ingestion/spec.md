# ingestion Specification

## Purpose

Once a data source is available locally, reqstool parses its files into the in-memory data model:
requirements, software verification cases, manual verification results, code annotations, and test
results. The ingestion capability defines which files are read, where they are expected, and how
default locations can be overridden.

## Requirements

### Requirement: Parse requirements

The system SHALL parse requirements from a `requirements.yml` file, producing requirement entities
with their identifier, title, significance, description, categories, and revision.

#### Scenario: Requirements file present

- **WHEN** a dataset contains a `requirements.yml` file
- **THEN** the system parses each requirement and its metadata into the model

### Requirement: Parse software verification cases

The system SHALL parse software verification cases from a `software_verification_cases.yml` file,
each linked to the requirements it verifies.

#### Scenario: SVC file present

- **WHEN** a dataset contains a `software_verification_cases.yml` file
- **THEN** the system parses each SVC and its requirement links into the model

### Requirement: Parse manual verification results

The system SHALL parse manual verification results from a `manual_verification_results.yml` file,
each linked to the SVC it verifies.

#### Scenario: MVR file present

- **WHEN** a dataset contains a `manual_verification_results.yml` file
- **THEN** the system parses each manual verification result into the model

### Requirement: Parse code annotations

The system SHALL parse code annotations from a generated `annotations.yml` file, capturing which code
elements implement requirements and which tests verify SVCs.

#### Scenario: Annotations file present

- **WHEN** a dataset contains a generated `annotations.yml` file
- **THEN** the system parses the implementation and test annotations into the model

### Requirement: Parse automated test results

The system SHALL parse automated test results from JUnit XML report files.

#### Scenario: JUnit results present

- **WHEN** JUnit XML report files are available for the dataset
- **THEN** the system parses the test outcomes and associates them with the model

### Requirement: Parse Karate test reports

The system SHALL parse test results from Karate test reports.

#### Scenario: Karate reports present

- **WHEN** Karate test reports are available for the dataset
- **THEN** the system parses their outcomes into the model

### Requirement: Static files at the content root

The system SHALL expect the static input files (`requirements.yml`, `software_verification_cases.yml`,
`manual_verification_results.yml`) at the root of the provided content path.

#### Scenario: Files located at content root

- **WHEN** the static input files reside at the root of the provided content path
- **THEN** the system locates and parses them without additional configuration

### Requirement: Configurable file locations

The system SHALL support an optional configuration file that overrides the default locations for
generated files and test reports.

#### Scenario: Configuration overrides defaults

- **WHEN** the dataset provides a reqstool configuration file that overrides default paths
- **THEN** the system reads generated files and test reports from the configured locations
