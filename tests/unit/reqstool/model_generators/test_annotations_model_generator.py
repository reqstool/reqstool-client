# Copyright © LFV

import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.model_generators.annotations_model_generator import AnnotationsModelGenerator
from reqstool.models.annotations import AnnotationsData

ANNOTATIONS_YML_FILE = "annotations.yml"
CURRENT_URN = "ms-001"


@pytest.fixture
def annotations_model_generator(resource_funcname_rootdir_w_path):
    return AnnotationsModelGenerator(uri=resource_funcname_rootdir_w_path(ANNOTATIONS_YML_FILE), urn=CURRENT_URN)


def test_annotations_model_generator(
    annotations_model_generator: AnnotationsModelGenerator, resource_funcname_rootdir_w_path
):
    assert annotations_model_generator.uri == resource_funcname_rootdir_w_path(ANNOTATIONS_YML_FILE)

    model: AnnotationsData = annotations_model_generator.model

    assert len(model.implementations) == 4

    assert len(model.implementations[UrnId(urn="ms-001", id="REQ_003")]) == 2

    assert model.implementations[UrnId(urn="ms-001", id="REQ_003")][0].element_kind == "CLASS"
    assert (
        model.implementations[UrnId(urn="ms-001", id="REQ_003")][0].fully_qualified_name
        == "se.lfv.common.annotations.requirements.resources.java.ImplRequirementsExample"
    )

    assert model.implementations[UrnId(urn="ms-001", id="REQ_003")][1].element_kind == "METHOD"
    assert (
        model.implementations[UrnId(urn="ms-001", id="REQ_003")][1].fully_qualified_name
        == "se.lfv.common.annotations.requirements.resources.java.ImplRequirementsExample.someMethod1"
    )

    assert len(model.tests) == 3

    assert len(model.tests[UrnId(urn="ms-001", id="REQ_003")]) == 2

    assert model.tests[UrnId(urn="ms-001", id="REQ_001")][0].element_kind == "CLASS"
    assert (
        model.tests[UrnId(urn="ms-001", id="REQ_001")][0].fully_qualified_name
        == "se.lfv.common.annotations.requirements.resources.java.TestRequirementsExample"
    )

    assert model.tests[UrnId(urn="ms-001", id="REQ_003")][1].element_kind == "METHOD"
    assert (
        model.tests[UrnId(urn="ms-001", id="REQ_003")][1].fully_qualified_name
        == "se.lfv.common.annotations.requirements.resources.java.TestRequirementsExample.someMethod"
    )
