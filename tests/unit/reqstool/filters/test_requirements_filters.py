# Copyright © LFV
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.raw_datasets import CombinedRawDataset


@SVCs("SVC_009", "SVC_010")
def test_include_exclude_for_requirements(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/sys-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset

    assert UrnId(urn="ext-001", id="REQ_ext001_100") in cids.requirements
    assert UrnId(urn="ext-002", id="REQ_ext002_200") not in cids.requirements
