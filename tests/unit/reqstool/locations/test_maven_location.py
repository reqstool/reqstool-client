# Copyright © LFV

from unittest.mock import MagicMock, patch

from reqstool.locations.maven_location import MavenLocation


def test_maven_location_token_defaults_to_none():
    loc = MavenLocation(group_id="com.example", artifact_id="my-lib", version="1.0.0")
    assert loc.token is None


def test_maven_location_make_available_no_token(tmp_path):
    loc = MavenLocation(group_id="com.example", artifact_id="my-lib", version="1.0.0")
    mock_downloader = MagicMock()
    mock_downloader.download.return_value = True
    extracted = str(tmp_path / "extracted")
    with (
        patch("reqstool.locations.maven_location.Downloader", return_value=mock_downloader) as mock_dl,
        patch("reqstool.locations.maven_location.Utils.extract_zip", return_value=extracted),
    ):
        result = loc._make_available_on_localdisk(str(tmp_path))
    assert result == extracted
    mock_dl.assert_called_once_with(base=loc.url, token=None)


def test_maven_location_make_available_with_token(tmp_path):
    loc = MavenLocation(group_id="com.example", artifact_id="my-lib", version="1.0.0", token="my-secret")
    mock_downloader = MagicMock()
    mock_downloader.download.return_value = True
    extracted = str(tmp_path / "extracted")
    with (
        patch("reqstool.locations.maven_location.Downloader", return_value=mock_downloader) as mock_dl,
        patch("reqstool.locations.maven_location.Utils.extract_zip", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))
    mock_dl.assert_called_once_with(base=loc.url, token="my-secret")


def test_maven_location_token_not_in_repr():
    loc = MavenLocation(group_id="com.example", artifact_id="my-lib", version="1.0.0", token="super-secret")
    assert "super-secret" not in repr(loc)
