# Copyright © LFV

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.exceptions import CircularImplementationError, CircularImportError, MissingRequirementsFileError
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators import combined_raw_datasets_generator
from reqstool.models.raw_datasets import CombinedRawDataset


@SVCs("SVC_001")
def test_basic_local(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_001")
def test_basic_requirements_config(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(
            path=local_testdata_resources_rootdir_w_path("test_basic/with_requirements_config/ms-101")
        ),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_001", "SVC_004")
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


@SVCs("SVC_001")
def test_standard_sys001_initial(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/sys-001")),
        semantic_validator=semantic_validator,
    )


@SVCs("SVC_020")
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


@SVCs("SVC_020")
def test_circular_import_raises(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    with pytest.raises(CircularImportError) as excinfo:
        combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
            initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_circular_import/node-a")),
            semantic_validator=semantic_validator,
        )
    assert "node-a" in str(excinfo.value)
    assert "Circular import detected" in str(excinfo.value)


@SVCs("SVC_020")
def test_circular_implementation_raises(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    with pytest.raises(CircularImplementationError) as excinfo:
        combined_raw_datasets_generator.CombinedRawDatasetsGenerator(
            initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_circular_impl/lib-a")),
            semantic_validator=semantic_validator,
        )
    assert "lib-a" in str(excinfo.value)
    assert "Circular implementation detected" in str(excinfo.value)


@SVCs("SVC_001")
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
