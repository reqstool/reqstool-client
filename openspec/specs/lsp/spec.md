# lsp Specification

## Purpose

The `lsp` command starts a Language Server Protocol server that exposes reqstool data to editors —
providing navigation, hover, and reqstool-specific details for requirement and SVC references in
source and data files. It is packaged behind an optional dependency extra.

## Requirements

### Requirement: Language server startup

The system SHALL start a Language Server Protocol server that serves reqstool data to a connected
editor client.

#### Scenario: Starting the server

- **WHEN** the user runs the lsp command
- **THEN** the system starts an LSP server ready to accept client connections

### Requirement: Transport selection

The system SHALL serve over stdio by default and SHALL support a TCP transport with a configurable
host and port.

#### Scenario: Default stdio transport

- **WHEN** the user starts the server without selecting a transport
- **THEN** the system communicates over stdio

#### Scenario: TCP transport

- **WHEN** the user selects the TCP transport with a host and port
- **THEN** the system listens for client connections on that host and port

### Requirement: Optional log file

The system SHALL support writing server logs to a file in addition to standard error.

#### Scenario: Log file configured

- **WHEN** the user supplies a log file path
- **THEN** the system writes server logs to that file as well as to standard error

### Requirement: Optional dependency guard

The system SHALL report a clear, actionable error when the optional dependencies required for the
language server are not installed.

#### Scenario: Missing extra

- **WHEN** the language-server dependencies are not installed
- **THEN** the system reports how to install them and does not start the server
