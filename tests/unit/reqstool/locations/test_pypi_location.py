# Copyright © LFV

from unittest.mock import patch

from reqstool.locations.pypi_location import PypiLocation


def test_pypi_location_token_defaults_to_none():
    loc = PypiLocation(package="my-package", version="1.0.0")
    assert loc.token is None


def test_pypi_location_make_available_no_token(tmp_path):
    loc = PypiLocation(package="my-package", version="1.0.0")
    extracted = str(tmp_path / "extracted")
    with (
        patch.object(PypiLocation, "get_package_url", return_value="https://example.com/pkg.tar.gz") as mock_url,
        patch("reqstool.locations.pypi_location.Utils.download_file", return_value=str(tmp_path / "pkg.tar.gz")),
        patch("reqstool.locations.pypi_location.Utils.extract_targz", return_value=extracted),
    ):
        result = loc._make_available_on_localdisk(str(tmp_path))
    assert result == extracted
    assert mock_url.call_args[0][3] is None


def test_pypi_location_make_available_with_token(tmp_path):
    loc = PypiLocation(package="my-package", version="1.0.0", token="bearer-secret")
    extracted = str(tmp_path / "extracted")
    with (
        patch.object(PypiLocation, "get_package_url", return_value="https://example.com/pkg.tar.gz") as mock_url,
        patch("reqstool.locations.pypi_location.Utils.download_file", return_value=str(tmp_path / "pkg.tar.gz")),
        patch("reqstool.locations.pypi_location.Utils.extract_targz", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))
    assert mock_url.call_args[0][3] == "bearer-secret"


def test_pypi_location_make_available_empty_string_token_treated_as_no_auth(tmp_path):
    loc = PypiLocation(package="my-package", version="1.0.0", token="")
    extracted = str(tmp_path / "extracted")
    with (
        patch.object(PypiLocation, "get_package_url", return_value="https://example.com/pkg.tar.gz") as mock_url,
        patch("reqstool.locations.pypi_location.Utils.download_file", return_value=str(tmp_path / "pkg.tar.gz")),
        patch("reqstool.locations.pypi_location.Utils.extract_targz", return_value=extracted),
    ):
        loc._make_available_on_localdisk(str(tmp_path))
    assert mock_url.call_args[0][3] is None


def test_pypi_location_token_not_in_repr():
    loc = PypiLocation(package="my-package", version="1.0.0", token="super-secret")
    assert "super-secret" not in repr(loc)
