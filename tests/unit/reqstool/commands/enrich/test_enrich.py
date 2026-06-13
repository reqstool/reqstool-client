# Copyright © LFV

import argparse
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.command import Command
from reqstool.commands.enrich.enrich import EnrichCommand
from reqstool.common.enrichment.enricher import BUILT_IN_PRESETS
from reqstool.locations.local_location import LocalLocation

_ENRICH_RESOURCES = Path(__file__).parents[4] / "resources" / "enrich"


def _load(fixture: str) -> tuple[str, str]:
    base = _ENRICH_RESOURCES / fixture
    return (base / "input.md").read_text(), (base / "expected.md").read_text()


@pytest.fixture()
def ms101(local_testdata_resources_rootdir_w_path):
    return LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))


@SVCs("SVC_ENRICH_0001")
def test_spec_all_fields(ms101):
    input_content, expected = _load("spec_all_fields")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:spec"])
    assert result.result == expected


@SVCs("SVC_ENRICH_0001")
def test_spec_no_description(ms101):
    input_content, expected = _load("spec_no_description")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:spec"])
    assert result.result == expected


@SVCs("SVC_ENRICH_0002")
def test_inline_title_only(ms101):
    input_content, expected = _load("inline_title_only")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:design"])
    assert result.result == expected


@SVCs("SVC_ENRICH_0001")
def test_inline_code_spans_skipped(ms101):
    input_content, expected = _load("inline_code_spans")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:design"])
    assert result.result == expected


@SVCs("SVC_ENRICH_0001")
def test_no_ids_passthrough(ms101):
    input_content, expected = _load("no_ids")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:spec"])
    assert result.result == expected


@SVCs("SVC_ENRICH_0003")
def test_command_enrich_reads_stdin_writes_output(monkeypatch):
    """ENRICH_0003: with no input file, the document is read from stdin and the result written to output."""
    out = io.StringIO()
    args = argparse.Namespace(
        source="local",
        path="/x",
        maven=None,
        npm=None,
        pypi=None,
        preset="openspec:spec",
        input=None,
        output=out,
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("document referencing REQ_X"))
    with (
        patch.object(Command, "_get_initial_source", return_value=MagicMock()),
        patch("reqstool.command.EnrichCommand") as mock_enrich,
    ):
        mock_enrich.return_value.result = "ENRICHED-OUTPUT"
        Command().command_enrich(args)
    assert out.getvalue() == "ENRICHED-OUTPUT"
    assert mock_enrich.call_args.kwargs["input_content"] == "document referencing REQ_X"


@SVCs("SVC_ENRICH_0004")
def test_command_enrich_no_source_no_config_exits(capsys):
    """ENRICH_0004: with neither an explicit source nor a config file, the command errors out."""
    args = argparse.Namespace(source=None, preset="openspec:spec", input=None, output=io.StringIO())
    with patch("reqstool.common.reqstool_ai_config.find_config", return_value=None):
        with pytest.raises(SystemExit) as exc:
            Command().command_enrich(args)
    assert exc.value.code == 2
    assert "reqstool enrich:" in capsys.readouterr().err


@SVCs("SVC_ENRICH_0001")
def test_mvr_enrichment(ms101):
    input_content, expected = _load("mvr")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:spec"])
    assert result.result == expected


@SVCs("SVC_ENRICH_0001")
def test_spec_multiline_description(ms101):
    input_content, expected = _load("spec_multiline_description")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:spec"])
    assert result.result == expected
