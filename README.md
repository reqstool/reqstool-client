
[![Commit Activity](https://img.shields.io/github/commit-activity/m/reqstool/reqstool-client?label=commits&style=for-the-badge)](https://github.com/reqstool/reqstool-client/pulse)
[![GitHub Issues](https://img.shields.io/github/issues/reqstool/reqstool-client?style=for-the-badge&logo=github)](https://github.com/reqstool/reqstool-client/issues)
[![License](https://img.shields.io/github/license/reqstool/reqstool-client?style=for-the-badge&logo=opensourceinitiative)](https://opensource.org/license/mit/)
[![Build](https://img.shields.io/github/actions/workflow/status/reqstool/reqstool-client/build.yml?style=for-the-badge&logo=github)](https://github.com/reqstool/reqstool-client/actions/workflows/build.yml)
[![Documentation](https://img.shields.io/badge/Documentation-blue?style=for-the-badge&link=docs)](https://reqstool.github.io)
[![GitHub Discussions](https://img.shields.io/github/discussions/reqstool/reqstool-client?style=for-the-badge&logo=github)](https://github.com/reqstool/reqstool-client/discussions)


# Reqstool Client

The reqstool command line client is the core tool for managing requirements traceability. It reads requirements, annotations, and test results to generate reports, exports, and status checks.

- **Status checks** -- verify that all requirements are implemented and tested, with an exit code for CI/CD gates
- **Reports** -- generate detailed reports in AsciiDoc or Markdown for auditors and stakeholders
- **JSON export** -- export data for custom tooling, with optional requirement/SVC filters

## Installation

### Prerequisites

- Python 3.13 or later
- pip or pipx

### Install with pipx (recommended)

```bash
pipx install reqstool
reqstool -h  # confirm installation
```

### Install with pip

```bash
pip install reqstool
reqstool -h  # confirm installation
```

## Usage

```bash
reqstool [-h] {report,export,status} {local,git,maven,pypi} ...
```

Use `-h/--help` for more information about each command and location.

## Editor and AI Integration

- **LSP** — language server for IDE features: hover, completion, go-to-definition, diagnostics, and outline view (`reqstool lsp`)
- **MCP** — tool server for AI agents (Claude, Copilot, etc.) to query requirements, SVCs, and traceability status (`reqstool mcp`)
- **reqstool-ai** — marketplace and plugins for reqstool and reqstool+OpenSpec integrations ([github.com/reqstool/reqstool-ai](https://github.com/reqstool/reqstool-ai))

## Documentation

Full documentation, including getting started guides for Java, Python, and TypeScript, can be found at [reqstool.github.io](https://reqstool.github.io).

## Contributing

See the organization-wide [CONTRIBUTING.md](https://github.com/reqstool/.github/blob/main/CONTRIBUTING.md).

## License

MIT License.
