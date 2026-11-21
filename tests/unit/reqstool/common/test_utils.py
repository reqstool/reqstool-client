# Copyright © LFV


from pathlib import PureWindowsPath
from urllib.parse import urlparse

import pytest
import requests

from reqstool.common.exceptions import EnvVarInterpolationError
from reqstool.common.utils import Utils


def test_check_ids_to_filter_plain_ids_get_urn_prepended():
    result = Utils.check_ids_to_filter(ids=["REQ_001", "REQ_002"], current_urn="ms-001")
    assert result == ["ms-001:REQ_001", "ms-001:REQ_002"]


def test_check_ids_to_filter_qualified_id_with_matching_urn_is_kept():
    result = Utils.check_ids_to_filter(ids=["ms-001:REQ_001"], current_urn="ms-001")
    assert result == ["ms-001:REQ_001"]


def test_check_ids_to_filter_qualified_id_with_foreign_urn_is_excluded():
    result = Utils.check_ids_to_filter(ids=["other-urn:REQ_001"], current_urn="ms-001")
    assert result == []


def test_check_ids_to_filter_mixed_ids():
    result = Utils.check_ids_to_filter(ids=["REQ_001", "ms-001:REQ_002", "other-urn:REQ_003"], current_urn="ms-001")
    assert "ms-001:REQ_001" in result
    assert "ms-001:REQ_002" in result
    assert "other-urn:REQ_003" not in result


def test_interpolate_env_vars_substitutes_braced_var(monkeypatch):
    monkeypatch.setenv("REQSTOOL_VERSION", "1.2.3")
    assert Utils.interpolate_env_vars("version: ${REQSTOOL_VERSION}") == "version: 1.2.3"


def test_interpolate_env_vars_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("REQSTOOL_VERSION", raising=False)
    assert Utils.interpolate_env_vars("version: ${REQSTOOL_VERSION:-9.9.9}") == "version: 9.9.9"


def test_interpolate_env_vars_default_overridden_when_set(monkeypatch):
    monkeypatch.setenv("REQSTOOL_VERSION", "1.2.3")
    assert Utils.interpolate_env_vars("version: ${REQSTOOL_VERSION:-9.9.9}") == "version: 1.2.3"


def test_interpolate_env_vars_unset_without_default_is_hard_error(monkeypatch):
    monkeypatch.delenv("REQSTOOL_MISSING", raising=False)
    with pytest.raises(EnvVarInterpolationError) as exc_info:
        Utils.interpolate_env_vars("version: ${REQSTOOL_MISSING}", source="requirements.yml")
    assert "REQSTOOL_MISSING" in str(exc_info.value)
    assert "requirements.yml" in str(exc_info.value)


def test_interpolate_env_vars_required_form_raises_custom_message(monkeypatch):
    monkeypatch.delenv("REQSTOOL_MISSING", raising=False)
    with pytest.raises(EnvVarInterpolationError) as exc_info:
        Utils.interpolate_env_vars("version: ${REQSTOOL_MISSING:?must be provided}")
    assert "must be provided" in str(exc_info.value)


def test_interpolate_env_vars_leaves_bare_dollar_and_schema_directive_untouched(monkeypatch):
    # bare $VAR is intentionally not expanded: $schema directives, regexes and
    # prices must survive unchanged.
    monkeypatch.delenv("schema", raising=False)
    text = "# yaml-language-server: $schema=https://example/schema.json\n" "note: price $5, regex ^foo$, literal $$"
    assert Utils.interpolate_env_vars(text) == text


def test_interpolate_env_vars_noop_on_text_without_placeholders():
    text = "version: 1.0.0\nname: reqstool\n"
    assert Utils.interpolate_env_vars(text) == text


# Issue #457: local files are read through requests-file, so the file: URI must be valid on Windows


@pytest.mark.parametrize(
    "path,expected",
    [
        ("\\\\?\\C:\\Users\\me\\requirements.yml", "C:\\Users\\me\\requirements.yml"),
        ("\\\\?\\UNC\\server\\share\\requirements.yml", "\\\\server\\share\\requirements.yml"),
        ("C:\\Users\\me\\requirements.yml", "C:\\Users\\me\\requirements.yml"),
        ("/home/me/requirements.yml", "/home/me/requirements.yml"),
    ],
)
def test_strip_windows_extended_length_prefix(path, expected):
    assert Utils.strip_windows_extended_length_prefix(path) == expected


class _FakeWindowsPath(PureWindowsPath):
    """Windows path semantics on any host (a real WindowsPath cannot be instantiated on POSIX)."""

    def absolute(self):
        return self


@pytest.mark.parametrize("path", ["C:\\Users\\me\\requirements.yml", "\\\\?\\C:\\Users\\me\\requirements.yml"])
def test_open_file_https_file_requests_hostless_file_uri_for_windows_path(monkeypatch, path):
    # Before the fix the request URL was "file://C:\\Users\\...", where requests-file reads "C:" as a host and
    # raises "file: URLs with hostname components are not permitted".
    monkeypatch.setattr("reqstool.common.utils.Path", _FakeWindowsPath)
    requested = []

    def fake_get(self, url, **kwargs):
        requested.append(url)
        return requests.Response()

    monkeypatch.setattr(requests.Session, "get", fake_get)

    Utils.open_file_https_file(path)

    assert requested == ["file:///C:/Users/me/requirements.yml"]
    assert urlparse(requested[0]).netloc == ""


def test_open_file_https_file_reads_path_with_reserved_characters(tmp_path):
    # "#" used to be sent unencoded and cut the path at the fragment
    directory = tmp_path / "my project #1"
    directory.mkdir()
    (directory / "requirements.yml").write_text("hello")

    response = Utils.open_file_https_file(str(directory / "requirements.yml"))

    assert response.status_code == 200
    assert response.text == "hello"


def test_to_file_uri_resolves_relative_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert Utils.to_file_uri("requirements.yml") == (tmp_path / "requirements.yml").as_uri()
