# Copyright © LFV

from unittest.mock import patch

from reqstool.locations.pypi_location import PypiLocation


def test_pypi_location_env_token_defaults_to_none():
    loc = PypiLocation(package="my-package", version="1.0.0")
    assert loc.env_token is None


def test_pypi_location_make_available_no_env_token(tmp_path):
    loc = PypiLocation(package="my-package", version="1.0.0")
    extracted = str(tmp_path / "extracted")
    with (
        patch.object(PypiLocation, "get_package_url", return_value="https://example.com/pkg.tar.gz"),
        patch("reqstool.locations.pypi_location.Utils.download_file", return_value=str(tmp_path / "pkg.tar.gz")),
        patch("reqstool.locations.pypi_location.Utils.extract_targz", return_value=extracted),
    ):
        result = loc._make_available_on_localdisk(str(tmp_path))
    assert result == extracted
