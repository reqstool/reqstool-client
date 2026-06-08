# enrich Specification

## Purpose

The `enrich` command rewrites a document that references reqstool IDs, injecting the corresponding
requirement, SVC, and MVR titles and descriptions in place. It lets external documents (for example
OpenSpec spec files) reference reqstool IDs while still rendering human-readable content, keeping
reqstool as the single source of truth.

## Requirements

### Requirement: Document enrichment

The system SHALL enrich an input document by injecting the titles and descriptions of the
requirement, SVC, and MVR IDs it references.

#### Scenario: Enriching referenced IDs

- **WHEN** an input document references reqstool requirement, SVC, or MVR IDs
- **THEN** the system injects the corresponding titles and descriptions into the document

### Requirement: Enrichment preset selection

The system SHALL apply a named enrichment preset that determines how references are detected and
rendered.

#### Scenario: Applying a preset

- **WHEN** the user selects a built-in enrichment preset
- **THEN** the system enriches the document according to that preset's rules

### Requirement: Input and output

The system SHALL read the document to enrich from a file or from standard input, and SHALL write the
result to a file or to standard output.

#### Scenario: Reading from stdin

- **WHEN** the user supplies no input file
- **THEN** the system reads the document from standard input

### Requirement: Dataset auto-detection

The system SHALL auto-detect the dataset from the reqstool AI configuration file in the current or an
ancestor directory when no source is provided, and SHALL report an error when none is found.

#### Scenario: Config found

- **WHEN** no source is given and a reqstool AI configuration file is found by walking up from the
  working directory
- **THEN** the system enriches against the dataset that configuration resolves to

#### Scenario: No config found

- **WHEN** no source is given and no reqstool AI configuration file is found
- **THEN** the system reports an error explaining how to provide a source
