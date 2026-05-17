# Copyright © LFV


import pytest

from reqstool.requirements_indata.requirements_indata_paths import RequirementsIndataPaths


# Define a fixture to create an instance for testing
@pytest.fixture
def default_instance():
    d = RequirementsIndataPaths()

    return d


# Test the prepend_paths method with properties that can be None
def test_prepend_paths_with_none_properties(default_instance):
    rip: RequirementsIndataPaths = default_instance

    assert rip.requirements_yml.path == "requirements.yml"
    assert rip.svcs_yml.path == "software_verification_cases.yml"
    assert rip.mvrs_yml.path == "manual_verification_results.yml"
    assert rip.annotations_yml.path == "annotations.yml"


def test_npm_location_path_resolution(tmp_path):
    """NpmLocation must use flat dst_path resolution (no symlink, no location.path prefix)."""
    import os
    from unittest.mock import patch

    from reqstool.locations.npm_location import NpmLocation
    from reqstool.requirements_indata.requirements_indata import RequirementsIndata

    # Create a minimal requirements.yml in tmp_path so path-check passes
    req_yml = tmp_path / "requirements.yml"
    req_yml.write_text("metadata:\n  urn: test\n  title: test\n")

    loc = NpmLocation(package="my-pkg-reqstool", version="1.0.0")

    # Patch _make_available_on_localdisk so RequirementsIndata can be constructed without a real download
    # Also patch _handle_requirements_config to skip YAML parsing
    with patch.object(NpmLocation, "_make_available_on_localdisk"):
        indata = RequirementsIndata.__new__(RequirementsIndata)
        object.__setattr__(indata, "dst_path", str(tmp_path))
        object.__setattr__(indata, "location", loc)
        object.__setattr__(indata, "reqstool_config", None)

        from reqstool.requirements_indata.requirements_indata_paths import RequirementsIndataPaths

        object.__setattr__(indata, "requirements_indata_paths", RequirementsIndataPaths())
        object.__setattr__(indata, "test_results_patterns", [])

        indata._ensure_absolute_paths_and_check_existance()

        # NpmLocation uses flat dst_path resolution — path should be absolute under tmp_path
        assert os.path.isabs(indata.requirements_indata_paths.requirements_yml.path)
        assert str(tmp_path) in indata.requirements_indata_paths.requirements_yml.path
