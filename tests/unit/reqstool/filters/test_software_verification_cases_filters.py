# Copyright © LFV
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.raw_datasets import CombinedRawDataset


@SVCs("SVC_011", "SVC_012")
def test_include_exclude_for_svcs(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset

    assert UrnId(urn="sys-001", id="SVC_sys001_500") in cids.svcs
    assert UrnId(urn="sys-001", id="SVC_sys001_600") in cids.svcs
    assert UrnId(urn="sys-001", id="SVC_sys001_000") not in cids.svcs
