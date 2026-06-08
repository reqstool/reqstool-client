# lifecycle Specification

## Purpose

Requirements and SVCs evolve over time and not every requirement is satisfied by source code. The
lifecycle capability defines how a requirement can declare a non-code implementation type, how
requirements and SVCs declare a lifecycle state, and how the system warns when superseded items are
still in use.

## Requirements

### Requirement: Non-code implementation types

The system SHALL allow a requirement to declare that it is satisfied by something other than source
code — not-applicable, configuration, platform, or framework — and SHALL not treat such a requirement
as unimplemented for lacking a code annotation.

#### Scenario: Configuration-satisfied requirement

- **WHEN** a requirement declares a non-code implementation type
- **THEN** the system shows the declared type instead of an implementation count and does not flag it
  as missing an implementation

### Requirement: Requirement lifecycle state

The system SHALL allow a requirement to declare a lifecycle state — draft, effective, deprecated, or
obsolete — with an optional reason, defaulting to effective.

#### Scenario: Deprecated requirement

- **WHEN** a requirement declares a deprecated lifecycle state
- **THEN** the system records that state and its reason for the requirement

### Requirement: SVC lifecycle state

The system SHALL allow an SVC to declare a lifecycle state — draft, effective, deprecated, or
obsolete — with an optional reason, defaulting to effective.

#### Scenario: Obsolete SVC

- **WHEN** an SVC declares an obsolete lifecycle state
- **THEN** the system records that state and its reason for the SVC

### Requirement: Superseded-reference warning

The system SHALL warn when a deprecated or obsolete requirement or SVC is still referenced by active
items.

#### Scenario: Active reference to a deprecated item

- **WHEN** an active item references a requirement or SVC that is deprecated or obsolete
- **THEN** the system logs a warning identifying the superseded reference
