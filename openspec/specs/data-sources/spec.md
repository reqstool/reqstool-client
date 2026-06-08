# data-sources Specification

## Purpose

Every reqstool command operates on a dataset that must first be located and made available locally.
The data-sources capability defines the supported source types — a local directory, a local packaged
artifact, or a remote artifact fetched from git, Maven, npm, or PyPI — and the common contract that
each source is materialized onto local disk before parsing. This behavior is shared by all commands
(status, report, export, validate, enrich, lsp, mcp).

## Requirements

### Requirement: Local materialization contract

The system SHALL make every selected source available on local disk before parsing, regardless of
source type.

#### Scenario: Source materialized before parsing

- **WHEN** a command is run against any source
- **THEN** the system places the source content in a local working directory before reading it

### Requirement: Local directory source

The system SHALL accept a path to a local directory as a data source.

#### Scenario: Local directory provided

- **WHEN** the user selects the local source with a directory path
- **THEN** the system uses the data found at that directory

### Requirement: Local packaged-artifact source

The system SHALL accept a local packaged artifact — a Maven ZIP, an npm tarball, or a PyPI source
distribution — as a data source and extract it before parsing.

#### Scenario: Local Maven ZIP provided

- **WHEN** the user selects the local source pointing at a Maven ZIP artifact
- **THEN** the system extracts the artifact and uses the data it contains

#### Scenario: Local npm or PyPI archive provided

- **WHEN** the user selects the local source pointing at an npm tarball or a PyPI source distribution
- **THEN** the system extracts the archive and uses the data it contains

### Requirement: Git repository source

The system SHALL fetch data from a git repository identified by URL, a path within the repository, and
a ref (branch, tag, or commit).

#### Scenario: Git source provided

- **WHEN** the user selects the git source with a URL, path, and ref
- **THEN** the system fetches the repository at that ref and uses the data at the given path

### Requirement: Maven artifact source

The system SHALL fetch a Maven artifact identified by group ID, artifact ID, and version, with an
optional repository URL and classifier.

#### Scenario: Maven coordinates provided

- **WHEN** the user selects the Maven source with group ID, artifact ID, and version
- **THEN** the system downloads the matching artifact and uses the data it contains

### Requirement: npm package source

The system SHALL fetch an npm package identified by package name and version, defaulting to the public
npm registry when no registry URL is given.

#### Scenario: npm package provided

- **WHEN** the user selects the npm source with a package name and version
- **THEN** the system downloads the package and uses the data it contains

### Requirement: PyPI package source

The system SHALL fetch a PyPI package identified by package name and version, with an optional index
URL.

#### Scenario: PyPI package provided

- **WHEN** the user selects the PyPI source with a package name and version
- **THEN** the system downloads the package and uses the data it contains

### Requirement: Authenticated access

The system SHALL accept an authentication token for remote sources, supplied as a direct value with
support for variable references in data files.

#### Scenario: Token supplied for a remote source

- **WHEN** the user provides a token for a git, Maven, npm, or PyPI source
- **THEN** the system uses that token to authenticate the fetch
