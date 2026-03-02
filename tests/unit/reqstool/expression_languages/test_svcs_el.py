# Copyright © LFV

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.expression_languages.svcs_el import SVCsELTransformer
from reqstool.models.svcs import VERIFICATIONTYPES, SVCData


@pytest.fixture
def create_tree():
    def closure(el: str):
        tree = SVCsELTransformer.parse_el(el)
        return tree

    return closure


@pytest.fixture
def svc_data():
    def closure(svc_id: str):
        return SVCData(
            id=UrnId.instance(svc_id),
            requirement_ids=["SVC_001", "SVC_002"],
            title="some title",
            description="some description",
            verification=VERIFICATIONTYPES("automated-test"),
            instructions="some instructions",
            revision="0.0.1",
        )

    return closure


def test_comp_id_equals_urn_completion(create_tree, svc_data):
    el = 'ids == "SVC_001"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is False

    el = 'ids == "SVC_001", "urn:SVC_101"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_999")).transform(tree) is False


def test_comp_id_not_equals(create_tree, svc_data):
    el = 'ids != "SVC_001"'

    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is False
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is True


@SVCs("SVC_014")
def test_comp_id_regex_equals(create_tree, svc_data):
    el = "ids == /urn\\:SVC_(\\d{2,3}|123)$/"
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:123")).transform(tree) is False
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_")).transform(tree) is False
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_1")).transform(tree) is False
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_01")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_1234")).transform(tree) is False
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_123")).transform(tree) is True


def test_id_op_and(create_tree, svc_data):
    el = 'ids == "SVC_001" and ids == "SVC_001"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is False

    el = 'ids == "SVC_001" and ids == "SVC_101"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is False
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is False


def test_id_op_or(create_tree, svc_data):
    el = 'ids == "SVC_001" or ids == "SVC_001"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is False

    el = 'ids == "SVC_001" or ids == "SVC_101"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is True
    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_101")).transform(tree) is True


def test_id_op_not(create_tree, svc_data):
    el = 'ids == "SVC_001"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is True

    el = 'not ids == "SVC_001"'
    tree = create_tree(el)

    assert SVCsELTransformer(urn="urn", data=svc_data("urn:SVC_001")).transform(tree) is False
