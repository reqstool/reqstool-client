# Copyright © LFV

import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.model_generators.mvrs_model_generator import MVRsModelGenerator

MVRS_YML_FILE = "manual_verification_results.yml"
URN = "ms-001"


@pytest.fixture
def mvrs_model_generator(resource_funcname_rootdir_w_path):
    return MVRsModelGenerator(uri=resource_funcname_rootdir_w_path(MVRS_YML_FILE), urn=URN)


def test_mvrs_model_generator(mvrs_model_generator: MVRsModelGenerator, resource_funcname_rootdir_w_path):
    assert mvrs_model_generator.uri == resource_funcname_rootdir_w_path(MVRS_YML_FILE)

    model = mvrs_model_generator.model

    assert len(model.results) == 2

    assert model.results[UrnId(urn="ms-001", id="MVR_001")].id.id == "MVR_001"
    assert model.results[UrnId(urn="ms-001", id="MVR_001")].svc_ids == [
        UrnId(urn="ms-001", id="SVC_001"),
        UrnId(urn="ms-001", id="SVC_002"),
    ]
    assert model.results[UrnId(urn="ms-001", id="MVR_001")].passed is True

    assert model.results[UrnId(urn="ms-001", id="MVR_002")].id.id == "MVR_002"
    assert model.results[UrnId(urn="ms-001", id="MVR_002")].svc_ids == [
        UrnId(urn="ms-001", id="SVC_201"),
        UrnId(urn="ms-001", id="SVC_202"),
    ]
    assert model.results[UrnId(urn="ms-001", id="MVR_002")].comment == "Failed due..."
    assert model.results[UrnId(urn="ms-001", id="MVR_002")].passed is False
