# imports-and-filtering Specification

## Purpose

A reqstool dataset can compose other datasets in two distinct ways: by **importing** them (pulling
their requirements in as the system's own) and by declaring **implementations** (pulling in evidence
that a used library satisfies requirements, without adopting the library's requirements as the
system's). Both are resolved recursively. Filters let a dataset include or exclude specific
requirements and SVCs from a composed source. This capability defines that composition and filtering
behavior.

## Requirements

### Requirement: Recursive import resolution

The system SHALL resolve a dataset's imports recursively, including the requirements of each imported
dataset and the imports they declare in turn.

#### Scenario: Nested imports

- **WHEN** a dataset imports another dataset that itself imports a third
- **THEN** the system includes requirements from all datasets in the import chain

### Requirement: Import cycle detection

The system SHALL detect a cycle in the import chain and reject it rather than recursing indefinitely.

#### Scenario: Circular import

- **WHEN** datasets import each other directly or transitively in a cycle
- **THEN** the system reports a circular-import error and stops

### Requirement: Recursive implementation resolution

The system SHALL resolve a dataset's declared implementations recursively, treating each implementing
dataset as one that may declare its own implementations.

#### Scenario: Nested implementations

- **WHEN** a dataset declares an implementation that itself declares a further implementation
- **THEN** the system follows the implementation chain to its full depth

### Requirement: Implementation cycle detection

The system SHALL detect a cycle in the implementation chain and reject it.

#### Scenario: Circular implementation

- **WHEN** datasets declare each other as implementations in a cycle
- **THEN** the system reports a circular-implementation error and stops

### Requirement: Implementation requirements excluded from scope

The system SHALL exclude the requirements contributed by implementation datasets from the system's
own requirement set, retaining only their verification evidence.

#### Scenario: Library requirements not counted as the system's

- **WHEN** an implementation dataset defines its own requirements
- **THEN** the system does not include those requirements in its own requirement set

### Requirement: Filter imported requirements

The system SHALL allow a dataset to include or exclude specific requirement IDs from a composed
source.

#### Scenario: Excluding a requirement

- **WHEN** a dataset applies a filter that excludes a requirement ID from a source
- **THEN** the composed dataset omits that requirement

### Requirement: Filter imported SVCs

The system SHALL allow a dataset to include or exclude specific SVC IDs from a composed source.

#### Scenario: Including specific SVCs

- **WHEN** a dataset applies a filter selecting specific SVC IDs from a source
- **THEN** the composed dataset includes only the selected SVCs from that source

### Requirement: Filter expression language

The system SHALL support a filter expression language combining logical operators, identifier
equality and inequality, and regular-expression matching.

#### Scenario: Compound filter expression

- **WHEN** a filter expression combines logical operators with identifier or regex matching
- **THEN** the system selects exactly the requirements or SVCs matching that expression
