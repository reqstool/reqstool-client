# Copyright © LFV

"""Text files are UTF-8, whatever the platform default encoding is.

On Windows ``open()`` without ``encoding=`` uses the ANSI code page (cp1252), so UTF-8 files written by editors or by
reqstool itself decode as mojibake or fail. These tests make the platform default strict ASCII, which rejects every
non-ASCII byte the same way, and then read non-ASCII UTF-8 files.
"""

import builtins
import logging
import pathlib

import pytest

NON_ASCII = "Måste stödja ✓ – ändå"


def _default_to_ascii(real):
    def wrapper(file, mode="r", *args, **kwargs):
        if "b" not in mode and kwargs.get("encoding") is None and len(args) < 2:
            kwargs["encoding"] = "ascii"
        return real(file, mode, *args, **kwargs)

    return wrapper


@pytest.fixture
def ascii_default_encoding(monkeypatch):
    """Return a function that makes ``open()`` default to ASCII inside the given module."""

    def apply(module):
        monkeypatch.setattr(module, "open", _default_to_ascii(builtins.open), raising=False)

    return apply


def test_lsp_schema_is_read_as_utf8(tmp_path, monkeypatch, ascii_default_encoding):
    from reqstool.lsp import yaml_schema

    (tmp_path / "x.schema.json").write_text(f'{{"title": "{NON_ASCII}"}}', encoding="utf-8")
    monkeypatch.setattr(yaml_schema, "SCHEMA_DIR", str(tmp_path))
    ascii_default_encoding(yaml_schema)

    assert yaml_schema.load_schema("x.schema.json") == {"title": NON_ASCII}


def test_lsp_definition_finds_id_in_utf8_yaml(tmp_path, ascii_default_encoding):
    from reqstool.lsp.features import definition

    yaml_file = tmp_path / "requirements.yml"
    yaml_file.write_text(f"requirements:\n  - title: {NON_ASCII}\n  - id: REQ_001\n", encoding="utf-8")
    ascii_default_encoding(definition)

    locations = definition.find_id_in_yaml(str(yaml_file), "REQ_001")

    assert [loc.range.start.line for loc in locations] == [2]


def test_lsp_definition_finds_reference_in_utf8_yaml(tmp_path, ascii_default_encoding):
    from reqstool.lsp.features import definition

    yaml_file = tmp_path / "software_verification_cases.yml"
    yaml_file.write_text(f"cases:\n  - description: {NON_ASCII}\n    requirement_ids: [REQ_001]\n", encoding="utf-8")
    ascii_default_encoding(definition)

    locations = definition._find_reference_in_yaml(str(yaml_file), "REQ_001")

    assert [loc.range.start.line for loc in locations] == [2]


def test_root_discovery_reads_utf8_ignore_file(tmp_path, ascii_default_encoding):
    from reqstool.lsp import root_discovery

    (tmp_path / ".reqstoolignore").write_text(f"# {NON_ASCII}\nbuild\n", encoding="utf-8")
    ascii_default_encoding(root_discovery)

    assert root_discovery._read_ignore_patterns(str(tmp_path)) == ["build"]


def test_root_discovery_parses_utf8_requirements_file(tmp_path, ascii_default_encoding):
    from reqstool.lsp import root_discovery

    (tmp_path / "requirements.yml").write_text(
        f"metadata:\n  urn: ms-001\n  variant: microservice\n  title: {NON_ASCII}\n", encoding="utf-8"
    )
    ascii_default_encoding(root_discovery)

    project = root_discovery._quick_parse(str(tmp_path))

    assert project is not None
    assert project.urn == "ms-001"


def test_reqstool_ai_config_is_read_as_utf8(tmp_path, ascii_default_encoding):
    from reqstool.common import reqstool_ai_config

    config = tmp_path / ".reqstool-ai.yaml"
    config.write_text(f"# {NON_ASCII}\nsystem:\n  path: docs\n", encoding="utf-8")
    ascii_default_encoding(reqstool_ai_config)

    assert reqstool_ai_config.resolve_system_path(config) == (tmp_path / "docs").resolve()


def test_json_schema_resource_is_read_as_utf8(monkeypatch):
    from reqstool.common.validators.syntax_validator import JsonSchemaItem

    real_read_text = pathlib.Path.read_text

    def read_text_ascii_default(self, encoding=None, errors=None, newline=None):
        return real_read_text(self, encoding=encoding or "ascii", errors=errors, newline=newline)

    monkeypatch.setattr(pathlib.Path, "read_text", read_text_ascii_default)

    # export_output.schema.json contains an em dash in a description
    assert JsonSchemaItem("export_output.schema.json").schema["$schema"]


def test_lsp_log_file_is_written_as_utf8(tmp_path, ascii_default_encoding):
    from reqstool.lsp.server import _log_handlers

    ascii_default_encoding(logging)
    log_file = tmp_path / "lsp.log"
    handlers = _log_handlers(str(log_file))
    try:
        for handler in handlers:
            handler.handle(logging.makeLogRecord({"msg": NON_ASCII, "levelno": logging.INFO, "levelname": "INFO"}))
    finally:
        for handler in handlers:
            handler.close()

    assert NON_ASCII in log_file.read_text(encoding="utf-8")
