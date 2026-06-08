# report Specification

## Purpose

The `report` command renders a human-readable document of all requirements and their verification
status from a reqstool dataset, suitable for inclusion in project documentation. It supports multiple
output formats and lets the reader organize requirements by grouping and sorting.

## Requirements

### Requirement: Report generation

The system SHALL generate a report from the collected statistics that lists every requirement
together with its implementation and verification status.

#### Scenario: Rendering a dataset

- **WHEN** the user runs the report command against a dataset
- **THEN** the system produces a document listing all requirements with their status

### Requirement: Output format selection

The system SHALL render the report in a selectable markup format, defaulting to AsciiDoc and also
supporting Markdown.

#### Scenario: Default format

- **WHEN** the user does not specify a format
- **THEN** the system renders the report as AsciiDoc

#### Scenario: Markdown requested

- **WHEN** the user selects the Markdown format
- **THEN** the system renders the report as Markdown

### Requirement: Grouping

The system SHALL group requirements in the report either by their initial-versus-imported origin or
by requirement category.

#### Scenario: Group by origin

- **WHEN** the user selects grouping by initial/imports
- **THEN** the system separates requirements belonging to the initial dataset from imported ones

#### Scenario: Group by category

- **WHEN** the user selects grouping by category
- **THEN** the system groups requirements by their first declared category

### Requirement: Sorting

The system SHALL sort the requirements within each group by one or more of: ID, significance, or
revision.

#### Scenario: Sorting by multiple keys

- **WHEN** the user supplies an ordered list of sort keys
- **THEN** the system orders requirements within each group by those keys in sequence

### Requirement: Output destination

The system SHALL write the report to a file when a path is given and to standard output otherwise.

#### Scenario: Output to file

- **WHEN** the user supplies an output file path
- **THEN** the system writes the report to that file, creating parent directories as needed

#### Scenario: Default to stdout

- **WHEN** the user supplies no output path
- **THEN** the system writes the report to standard output

### Requirement: Deprecated AsciiDoc alias

The system SHALL retain a deprecated dedicated AsciiDoc report command that behaves like the report
command in AsciiDoc format while warning the user to migrate.

#### Scenario: Invoking the deprecated alias

- **WHEN** the user invokes the deprecated AsciiDoc report command
- **THEN** the system emits a deprecation warning and produces the AsciiDoc report
