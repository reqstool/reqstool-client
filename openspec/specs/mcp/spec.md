# mcp Specification

## Purpose

The `mcp` command starts a Model Context Protocol server that exposes a reqstool dataset to AI
agents through structured tools (status, requirement listing, and more). It is packaged behind an
optional dependency extra and is designed so the same configuration works for every contributor.

## Requirements

### Requirement: MCP server startup

The system SHALL start a Model Context Protocol server that exposes the reqstool dataset to connected
clients through structured tools.

#### Scenario: Starting the server

- **WHEN** the user runs the mcp command
- **THEN** the system starts an MCP server serving the resolved dataset

### Requirement: Transport selection

The system SHALL support stdio, SSE, and streamable-HTTP transports, defaulting to stdio, with a
configurable host and port for the HTTP transports.

#### Scenario: Default stdio transport

- **WHEN** the user starts the server without selecting a transport
- **THEN** the system communicates over stdio

#### Scenario: HTTP transport

- **WHEN** the user selects an HTTP-based transport with a host and port
- **THEN** the system serves on that host and port

### Requirement: Dataset resolution

The system SHALL serve an explicitly provided source, or auto-detect the dataset from the reqstool AI
configuration file in the current or an ancestor directory when no source is given, and SHALL report
an error when neither is available.

#### Scenario: Auto-detected dataset

- **WHEN** no source is given and a reqstool AI configuration file is found by walking up from the
  working directory
- **THEN** the system serves the dataset that configuration resolves to

#### Scenario: No source and no config

- **WHEN** no source is given and no reqstool AI configuration file is found
- **THEN** the system reports an error explaining how to provide a source

### Requirement: Optional dependency guard

The system SHALL report a clear, actionable error when the optional dependencies required for the MCP
server are not installed.

#### Scenario: Missing extra

- **WHEN** the MCP dependencies are not installed
- **THEN** the system reports how to install them and does not start the server
