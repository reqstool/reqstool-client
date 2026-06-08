# export Specification

## Purpose

The `export` command serializes a reqstool dataset for consumption by other tools — either as a
structured JSON document conforming to the export schema, or as a raw SQLite database snapshot. It
replaces the deprecated `generate-json` command.

## Requirements

### Requirement: JSON export

The system SHALL export the dataset as a JSON document conforming to the export schema, as the default
format.

#### Scenario: Exporting to JSON

- **WHEN** the user runs export without specifying a format
- **THEN** the system emits a JSON document of the dataset

### Requirement: Export filtering

The system SHALL allow the JSON export to be restricted to a specified set of requirement IDs or SVC
IDs.

#### Scenario: Filtering by requirement IDs

- **WHEN** the user supplies one or more requirement IDs
- **THEN** the system restricts the exported document to those requirements and their related entities

### Requirement: Unfiltered export

The system SHALL provide an option to export the dataset without applying the dataset's own
import/scope filters.

#### Scenario: Exporting unfiltered data

- **WHEN** the user requests an unfiltered export
- **THEN** the system includes all data without applying filters

### Requirement: SQLite export

The system SHALL be able to export the dataset as a SQLite database snapshot written to a file.

#### Scenario: Exporting to SQLite

- **WHEN** the user selects the SQLite format and supplies an output file path
- **THEN** the system writes a SQLite database snapshot of the dataset to that file

#### Scenario: SQLite without an output file

- **WHEN** the user selects the SQLite format but supplies no output file path
- **THEN** the system reports an error and does not produce output

### Requirement: Output destination

The system SHALL write the JSON export to a file when a path is given and to standard output
otherwise.

#### Scenario: Default to stdout

- **WHEN** the user requests a JSON export with no output path
- **THEN** the system writes the JSON to standard output
