# Contributing to reqstool-client

Thank you for your interest in contributing!

For DCO sign-off, commit conventions, and code review process, see the organization-wide [CONTRIBUTING.md](https://github.com/reqstool/.github/blob/main/CONTRIBUTING.md).

## Prerequisites

- Python 3.10+
- [Hatch](https://hatch.pypa.io/) (`pip install hatch`)

## Setup

```bash
git clone https://github.com/reqstool/reqstool-client.git
cd reqstool-client
hatch env create dev
```

## Build & Test

```bash
# Run all tests
hatch run dev:pytest --cov=reqstool

# Unit tests only
hatch run dev:pytest --cov=reqstool tests/unit

# Integration tests only
hatch run dev:pytest --cov=reqstool tests/integration
```

## Linting & Formatting

```bash
# Format with black
hatch run dev:black src tests

# Lint with flake8
hatch run dev:flake8
```

## Model Generation

Pydantic data models in `src/reqstool/models/generated/` are auto-generated from the JSON Schemas
in `src/reqstool/resources/schemas/v1/`. **JSON Schema is the source of truth** — never edit the
generated files directly.

To regenerate after modifying a schema:

```bash
hatch run dev:codegen
```

This runs `datamodel-codegen` to produce Pydantic v2 `BaseModel` classes from all schema files.
The generated files should be committed alongside the schema changes.
