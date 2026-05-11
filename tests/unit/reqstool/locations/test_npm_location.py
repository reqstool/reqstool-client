# Copyright © LFV

from unittest.mock import MagicMock, patch

import pytest

from reqstool.locations.npm_location import NpmLocation


def test_npm_location_defaults():
    loc = NpmLocation(package="@scope/my-pkg-reqstool", version="1.2.3")
    assert loc.url == "https://registry.npmjs.org"
    assert loc.env_token is None


def test_npm_location_custom_registry():
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0", url="https://my.registry.example.com")
    assert loc.url == "https://my.registry.example.com"


def test_npm_location_make_available_no_token(tmp_path):
    loc = NpmLocation(package="@scope/my-pkg-reqstool", version="1.2.3")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    extracted = str(tmp_path / "package")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", return_value=extracted),
    ):
        result = loc._make_available_on_localdisk(str(tmp_path))

    assert result == extracted


def test_npm_location_make_available_with_token(tmp_path, monkeypatch):
    monkeypatch.setenv("NPM_TOKEN", "secret-token")
    loc = NpmLocation(package="my-pkg-reqstool", version="2.0.0", env_token="NPM_TOKEN")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    extracted = str(tmp_path / "package")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response) as mock_get,
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", return_value=extracted),
    ):
        result = loc._make_available_on_localdisk(str(tmp_path))

    call_headers = mock_get.call_args[1]["headers"]
    assert call_headers["Authorization"] == "Bearer secret-token"
    assert result == extracted


def test_npm_location_raises_when_tarball_missing(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {}}  # no tarball key

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        pytest.raises(Exception, match="dist.tarball"),
    ):
        loc._make_available_on_localdisk(str(tmp_path))
