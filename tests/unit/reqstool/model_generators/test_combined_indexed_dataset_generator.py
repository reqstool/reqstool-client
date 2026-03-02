# Copyright © LFV

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.raw_datasets import CombinedRawDataset


def test_basic_baseline(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    cids = CombinedIndexedDatasetGenerator(_crd=crd)

    assert cids is not None


def test_standard_baseline_ms001_no_filtering(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=False).combined_indexed_dataset

    assert len(cids.requirements) == 8


@SVCs("SVC_005")
def test_standard_baseline_ms001(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset

    # check reqs
    assert len(cids.requirements) == 6
    assert UrnId.instance("ms-001:REQ_010") in cids.requirements
    assert UrnId.instance("ms-001:REQ_020") in cids.requirements
    assert UrnId.instance("sys-001:REQ_sys001_505") in cids.requirements
    assert UrnId.instance("ext-001:REQ_ext001_100") in cids.requirements
    assert UrnId.instance("ext-002:REQ_ext002_300") in cids.requirements
    assert UrnId.instance("ext-002:REQ_ext002_400") in cids.requirements


def test_standard_baseline_sys001(resource_funcname_rootdir, local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/sys-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets

    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset

    assert cids.initial_model_urn == "sys-001"


@pytest.fixture
def cids_mvr_exclusion(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_delete_mvr/ms-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets
    return CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset


def test_mvr_excluded_when_sole_referenced_svc_is_excluded(cids_mvr_exclusion):
    # MVR_ms001_001 references only SVC_sys001_B which is excluded by the SVC filter
    # since its only referenced SVC is excluded, the MVR is cascade-excluded
    assert UrnId.instance("ms-001:MVR_ms001_001") not in cids_mvr_exclusion.mvrs


def test_mvr_included_when_at_least_one_referenced_svc_is_included(cids_mvr_exclusion):
    # MVR_ms001_002 references both SVC_sys001_A (included) and SVC_sys001_B (excluded)
    # since one referenced SVC remains, the MVR is included
    assert UrnId.instance("ms-001:MVR_ms001_002") in cids_mvr_exclusion.mvrs


def test_excluded_svc_removed_from_included_mvr_svc_ids(cids_mvr_exclusion):
    # after SVC_sys001_B is excluded, MVR_ms001_002's svc_ids should only contain SVC_sys001_A
    mvr = cids_mvr_exclusion.mvrs[UrnId.instance("ms-001:MVR_ms001_002")]
    assert UrnId.instance("sys-001:SVC_sys001_B") not in mvr.svc_ids
    assert UrnId.instance("sys-001:SVC_sys001_A") in mvr.svc_ids


def test_excluded_svc_not_present_after_filtering(cids_mvr_exclusion):
    assert UrnId.instance("sys-001:SVC_sys001_B") not in cids_mvr_exclusion.svcs


def test_included_svc_present_after_filtering(cids_mvr_exclusion):
    assert UrnId.instance("sys-001:SVC_sys001_A") in cids_mvr_exclusion.svcs


def test_svc_custom_includes_without_custom_excludes_does_not_crash(
    resource_funcname_rootdir, local_testdata_resources_rootdir_w_path
):
    """Regression test for #233: SVC filter with custom includes but no custom excludes must not crash."""
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets
    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset
    assert cids is not None


def test_req_custom_includes_without_custom_excludes_does_not_crash(
    resource_funcname_rootdir, local_testdata_resources_rootdir_w_path
):
    """Regression test for #233: requirement filter with custom includes but no custom excludes must not crash."""
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    crd: CombinedRawDataset = CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/sys-001")),
        semantic_validator=semantic_validator,
    ).combined_raw_datasets
    cids = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset
    assert cids is not None


def test_deleted_req_not_in_remaining_svc_requirement_ids(cids_mvr_exclusion):
    for svc_urn_id, svcdata in cids_mvr_exclusion.svcs.items():
        for req_id in svcdata.requirement_ids:
            assert req_id in cids_mvr_exclusion.requirements


def test_deleted_svc_not_in_remaining_mvr_svc_ids(cids_mvr_exclusion):
    for mvr_urn_id, mvrdata in cids_mvr_exclusion.mvrs.items():
        for svc_id in mvrdata.svc_ids:
            assert svc_id in cids_mvr_exclusion.svcs


def test_reqs_from_urn_consistent_after_filtering(cids_mvr_exclusion):
    for urn, req_ids in cids_mvr_exclusion.reqs_from_urn.items():
        for req_id in req_ids:
            assert req_id in cids_mvr_exclusion.requirements


def test_svcs_from_req_consistent_after_filtering(cids_mvr_exclusion):
    for req_id, svc_ids in cids_mvr_exclusion.svcs_from_req.items():
        assert req_id in cids_mvr_exclusion.requirements
        for svc_id in svc_ids:
            assert svc_id in cids_mvr_exclusion.svcs
