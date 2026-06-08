# Copyright © LFV

from pathlib import Path

import pytest

from reqstool_python_decorators.decorators.decorators import SVCs

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


@SVCs("SVC_ENRICH_0003")
def test_no_ids_passthrough(ms101):
    input_content, expected = _load("no_ids")
    result = EnrichCommand(location=ms101, input_content=input_content, config=BUILT_IN_PRESETS["openspec:spec"])
    assert result.result == expected


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
