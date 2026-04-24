# Copyright © LFV

from unittest.mock import MagicMock, patch

from reqstool.locations.maven_location import MavenLocation


def test_maven_location_env_token_defaults_to_none():
    loc = MavenLocation(group_id="com.example", artifact_id="my-lib", version="1.0.0")
    assert loc.env_token is None


def test_maven_location_make_available_no_env_token(tmp_path):
    loc = MavenLocation(group_id="com.example", artifact_id="my-lib", version="1.0.0")
    mock_downloader = MagicMock()
    mock_downloader.download.return_value = True
    extracted = str(tmp_path / "extracted")
    with (
        patch("reqstool.locations.maven_location.Downloader", return_value=mock_downloader),
        patch("reqstool.locations.maven_location.Utils.extract_zip", return_value=extracted),
    ):
        result = loc._make_available_on_localdisk(str(tmp_path))
    assert result == extracted
