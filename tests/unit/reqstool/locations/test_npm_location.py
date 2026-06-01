# Copyright © LFV

from unittest.mock import MagicMock, patch

import pytest

from reqstool.common.exceptions import ArtifactDownloadError, ArtifactExtractionError
from reqstool.locations.npm_location import NpmLocation


def test_npm_location_defaults():
    loc = NpmLocation(package="@scope/my-pkg-reqstool", version="1.2.3")
    assert loc.url == "https://registry.npmjs.org"
    assert loc.token is None


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


def test_npm_location_make_available_with_token(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="2.0.0", token="secret-token")

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
        pytest.raises(ArtifactDownloadError, match="dist.tarball"),
    ):
        loc._make_available_on_localdisk(str(tmp_path))


def test_npm_location_raises_on_http_error(tmp_path):
    import requests as req

    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("404 Not Found")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        pytest.raises(ArtifactDownloadError),
    ):
        loc._make_available_on_localdisk(str(tmp_path))


def test_npm_location_raises_on_extraction_error(tmp_path):
    import tarfile

    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", side_effect=tarfile.TarError("bad tar")),
        pytest.raises(ArtifactExtractionError),
    ):
        loc._make_available_on_localdisk(str(tmp_path))


def test_npm_location_rejects_http_registry_url():
    with pytest.raises(Exception, match="https"):
        NpmLocation(package="my-pkg-reqstool", version="1.0.0", url="http://my.registry.example.com")


def test_npm_location_blocks_ssrf_tarball_host_mismatch(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    # tarball served from a different host than the registry
    mock_response.json.return_value = {"dist": {"tarball": "https://evil.internal/tarball.tgz"}}

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        pytest.raises(ArtifactDownloadError, match="SSRF"),
    ):
        loc._make_available_on_localdisk(str(tmp_path))


def test_npm_location_blocks_http_tarball_url(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "http://registry.npmjs.org/tarball.tgz"}}

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        pytest.raises(ArtifactDownloadError, match="SSRF"),
    ):
        loc._make_available_on_localdisk(str(tmp_path))


def test_npm_location_raises_on_oversized_metadata(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.content = b"x" * (10 * 1024 * 1024 + 1)

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response),
        pytest.raises(ArtifactDownloadError, match="size limit"),
    ):
        loc._make_available_on_localdisk(str(tmp_path))


def test_npm_location_scoped_package_slash_is_percent_encoded(tmp_path):
    loc = NpmLocation(package="@scope/my-pkg-reqstool", version="1.2.3")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    extracted = str(tmp_path / "package")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response) as mock_get,
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))

    called_url = mock_get.call_args[0][0]
    assert "@scope%2Fmy-pkg-reqstool" in called_url
    assert "/@scope/" not in called_url  # raw slash must not appear in the package segment


def test_npm_location_version_url_encoded(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    extracted = str(tmp_path / "package")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response) as mock_get,
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))

    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/1.0.0")


def test_npm_location_get_tarball_uses_timeout(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    extracted = str(tmp_path / "package")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response) as mock_get,
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))

    assert mock_get.call_args[1].get("timeout") == 30


def test_npm_location_make_available_no_token_sends_no_auth(tmp_path):
    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist": {"tarball": "https://registry.npmjs.org/tarball.tgz"}}

    extracted = str(tmp_path / "package")

    with (
        patch("reqstool.locations.npm_location.requests.get", return_value=mock_response) as mock_get,
        patch("reqstool.locations.npm_location.Utils.download_file", return_value=tmp_path / "tarball.tgz"),
        patch("reqstool.locations.npm_location.Utils.extract_targz", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))

    assert "Authorization" not in mock_get.call_args[1]["headers"]
