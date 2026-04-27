# Copyright © LFV

from pathlib import Path

import pytest

from reqstool.common.reqstool_ai_config import CONFIG_FILENAME, find_config, resolve_system_path


def test_find_config_in_cwd(tmp_path: Path, monkeypatch):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("system:\n  path: docs/reqstool\n")
    monkeypatch.chdir(tmp_path)
    assert find_config() == cfg.resolve()


def test_find_config_in_ancestor(tmp_path: Path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("system:\n  path: docs/reqstool\n")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert find_config(start=deep) == cfg.resolve()


def test_find_config_missing(tmp_path: Path):
    assert find_config(start=tmp_path) is None


def test_resolve_system_path_relative(tmp_path: Path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("system:\n  path: docs/reqstool\n")
    assert resolve_system_path(cfg) == (tmp_path / "docs" / "reqstool").resolve()


def test_resolve_system_path_absolute(tmp_path: Path):
    target = tmp_path / "elsewhere"
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text(f"system:\n  path: {target}\n")
    assert resolve_system_path(cfg) == target.resolve()


def test_resolve_system_path_missing_system(tmp_path: Path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("urn: x\n")
    with pytest.raises(ValueError, match="missing required 'system' mapping"):
        resolve_system_path(cfg)


def test_resolve_system_path_missing_path(tmp_path: Path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("system:\n  not_path: y\n")
    with pytest.raises(ValueError, match="missing required 'system.path' string"):
        resolve_system_path(cfg)


def test_resolve_system_path_empty_file(tmp_path: Path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("")
    with pytest.raises(ValueError, match="missing required 'system' mapping"):
        resolve_system_path(cfg)


def test_find_config_stops_at_first_match(tmp_path: Path):
    outer_cfg = tmp_path / CONFIG_FILENAME
    outer_cfg.write_text("system:\n  path: outer\n")
    inner = tmp_path / "inner"
    inner.mkdir()
    inner_cfg = inner / CONFIG_FILENAME
    inner_cfg.write_text("system:\n  path: inner\n")
    assert find_config(start=inner) == inner_cfg.resolve()
