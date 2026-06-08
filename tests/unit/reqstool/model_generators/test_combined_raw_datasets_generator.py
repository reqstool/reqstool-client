# Copyright © LFV

import contextlib
import re
from unittest.mock import patch

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.exceptions import CircularImplementationError, CircularImportError, MissingRequirementsFileError
from reqstool.common.utils import TempDirectoryManager
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.location_resolver.location_resolver import LocationResolver
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.pypi_location import PypiLocation
from reqstool.model_generators import combined_raw_datasets_generator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.raw_datasets import CombinedRawDataset


@SVCs("SVC_INGEST_0001")
def test_basic_local(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_INGEST_0001")
def test_basic_requirements_config(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(
            path=local_testdata_resources_rootdir_w_path("test_basic/with_requirements_config/ms-101")
        ),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_INGEST_0001")
def test_standard_ms001_initial(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())

    crd: CombinedRawDataset = combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    # assert all referenced variants are found during parsing
    assert len(crd.raw_datasets) == 4

    # assert requirements.yml parsing
    assert len(crd.raw_datasets["ms-001"].requirements_data.requirements) == 2
    assert len(crd.raw_datasets["sys-001"].requirements_data.requirements) == 1
    assert len(crd.raw_datasets["ext-001"].requirements_data.requirements) == 2
    assert len(crd.raw_datasets["ext-002"].requirements_data.requirements) == 3

    # assert svcs parsing

    assert len(crd.raw_datasets["ms-001"].svcs_data.cases) == 7
    assert len(crd.raw_datasets["sys-001"].svcs_data.cases) == 3
    assert crd.raw_datasets["ext-001"].svcs_data is None
    assert crd.raw_datasets["ext-002"].svcs_data is None

    # assert mvrs parsing

    assert len(crd.raw_datasets["ms-001"].mvrs_data.results) == 2
    assert crd.raw_datasets["sys-001"].mvrs_data is None
    assert crd.raw_datasets["ext-001"].mvrs_data is None
    assert crd.raw_datasets["ext-002"].mvrs_data is None


@SVCs("SVC_INGEST_0001")
def test_standard_sys001_initial(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/sys-001")),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_PARSE_0002")
def test_missing_requirements_file(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    with pytest.raises(MissingRequirementsFileError) as excinfo:
        combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
            initial_location=LocalLocation(
                path=local_testdata_resources_rootdir_w_path("this/path/does/not/have/a/requirements/file")
            ),
            semantic_validator=semantic_validator,
        )
    assert "this/path/does/not/have/a/requirements/file" in str(excinfo.value)


@SVCs("SVC_PARSE_0002")
def test_circular_import_raises(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    with pytest.raises(CircularImportError) as excinfo:
        combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
            initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_circular_import/node-a")),
            semantic_validator=semantic_validator,
        )
    assert "node-a" in str(excinfo.value)
    assert "Circular import detected" in str(excinfo.value)


@SVCs("SVC_PARSE_0002")
def test_circular_implementation_raises(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    with pytest.raises(CircularImplementationError) as excinfo:
        combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
            initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_circular_impl/lib-a")),
            semantic_validator=semantic_validator,
        )
    assert "lib-a" in str(excinfo.value)
    assert "Circular implementation detected" in str(excinfo.value)


@SVCs("SVC_INGEST_0001")
def test_implementation_traversal_recursive(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())

    crd: CombinedRawDataset = combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_recursive_impl/root")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    # all four nodes are in raw_datasets (recursive traversal reached lib-b and lib-c)
    assert set(crd.raw_datasets.keys()) == {"root", "lib-a", "lib-b", "lib-c"}

    # implementation nodes are parsed (requirements present in raw_datasets)
    assert len(crd.raw_datasets["lib-a"].requirements_data.requirements) == 1
    assert len(crd.raw_datasets["lib-b"].requirements_data.requirements) == 1
    assert len(crd.raw_datasets["lib-c"].requirements_data.requirements) == 1

    # implementation edges are tagged correctly in the parsing graph
    assert ("lib-a", "implementation") in crd.parsing_graph["root"]
    assert ("lib-b", "implementation") in crd.parsing_graph["lib-a"]
    assert ("lib-c", "implementation") in crd.parsing_graph["lib-b"]


@contextlib.contextmanager
def _capture_suffix_calls():
    captured = []
    original = TempDirectoryManager.get_suffix_path

    def _capturing(self, suffix):
        captured.append(suffix)
        return original(self, suffix)

    with patch.object(TempDirectoryManager, "get_suffix_path", _capturing):
        yield captured


def _assert_safe_suffix(suffix, expected_prefix, uri_fragment):
    assert len(suffix) >= 1, "get_suffix_path was never called"
    assert suffix.startswith(expected_prefix)
    assert uri_fragment in suffix
    assert re.match(r"^[a-zA-Z0-9._-]+$", suffix), f"Suffix contains unsafe chars: {suffix!r}"


@SVCs("SVC_PARSE_0002")
def test_tmpdir_suffix_local_uses_local_prefix():
    with _capture_suffix_calls() as captured_suffixes:
        with pytest.raises(MissingRequirementsFileError):
            CombinedRawDatasetsGenerator(
                initial_location=LocalLocation(path="/nonexistent/path"),
                semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
            )
    assert len(captured_suffixes) >= 1, "get_suffix_path was never called"
    _assert_safe_suffix(captured_suffixes[0], "local_", "nonexistent")


@SVCs("SVC_PARSE_0002")
@pytest.mark.parametrize(
    "location,expected_prefix,uri_fragment",
    [
        (GitLocation(url="https://github.com/org/repo", ref="main"), "git_", "github.com"),
        (MavenLocation(group_id="com.example", artifact_id="my-artifact", version="1.0.0"), "maven_", "my-artifact"),
        (PypiLocation(package="my-package", version="1.0.0"), "pypi_", "my-package"),
    ],
)
def test_tmpdir_suffix_remote_uses_location_type_prefix(tmp_path, location, expected_prefix, uri_fragment):
    with _capture_suffix_calls() as captured_suffixes:
        with patch.object(LocationResolver, "make_available_on_localdisk", return_value=str(tmp_path)):
            with pytest.raises(MissingRequirementsFileError):
                CombinedRawDatasetsGenerator(
                    initial_location=location,
                    semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
                )
    assert len(captured_suffixes) >= 1, "get_suffix_path was never called"
    _assert_safe_suffix(captured_suffixes[0], expected_prefix, uri_fragment)
