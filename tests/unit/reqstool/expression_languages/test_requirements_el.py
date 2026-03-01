# Copyright © LFV

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.expression_languages.requirements_el import RequirementsELTransformer
from reqstool.models.requirements import SIGNIFANCETYPES, RequirementData


@pytest.fixture
def create_tree():
    def closure(el: str):
        tree = RequirementsELTransformer.parse_el(el)

        return tree

    return closure


@pytest.fixture
def requirement_data():
    def closure(req_id: str):
        return RequirementData(
            id=UrnId.instance(req_id),
            title="some title",
            significance=SIGNIFANCETYPES("shall"),
            description="some description",
            rationale="some rationale",
            categories=["maintainability", "functional-suitability"],
            references=None,
            revision="0.0.1",
        )

    return closure


def test_comp_id_equals_urn_completion(create_tree, requirement_data):
    el = 'ids == "REQ_001"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is False

    el = 'ids == "REQ_001", "urn:REQ_101"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_999")).transform(tree) is False


def test_comp_id_equals(create_tree, requirement_data):
    el = 'ids == "REQ_001"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is False

    el = 'ids == "REQ_001", "REQ_101"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_999")).transform(tree) is False


def test_comp_id_not_equals(create_tree, requirement_data):
    el = 'ids != "REQ_001"'

    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is False
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is True


@SVCs("SVC_013")
def test_comp_id_regex_equals(create_tree, requirement_data):
    el = "ids == /urn\\:REQ_(\\d{2,3}|123)$/"
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:123")).transform(tree) is False
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_")).transform(tree) is False
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_1")).transform(tree) is False
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_01")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_1234")).transform(tree) is False
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_123")).transform(tree) is True


def test_id_op_and(create_tree, requirement_data):
    el = 'ids == "REQ_001" and ids == "REQ_001"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is False

    el = 'ids == "REQ_001" and ids == "REQ_101"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is False
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is False


def test_id_op_or(create_tree, requirement_data):
    el = 'ids == "REQ_001" or ids == "REQ_001"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is False

    el = 'ids == "REQ_001" or ids == "REQ_101"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True
    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_101")).transform(tree) is True


def test_id_op_not(create_tree, requirement_data):
    el = 'ids == "REQ_001"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is True

    el = 'not ids == "REQ_001"'
    tree = create_tree(el)

    assert RequirementsELTransformer(urn="urn", data=requirement_data("urn:REQ_001")).transform(tree) is False


# ---------------------------------------------------------------------------
# Negative-path: parse errors
# ---------------------------------------------------------------------------


def test_parse_el_invalid_operator_raises():
    """An unsupported operator raises a parse error."""
    with pytest.raises(Exception):
        RequirementsELTransformer.parse_el('ids > "REQ_001"')


def test_parse_el_unbalanced_parens_raises():
    """Unbalanced parentheses raise a parse error."""
    with pytest.raises(Exception):
        RequirementsELTransformer.parse_el('(ids == "REQ_001"')


def test_parse_el_empty_string_raises():
    """An empty expression string raises a parse error."""
    with pytest.raises(Exception):
        RequirementsELTransformer.parse_el("")


def test_parse_el_garbage_syntax_raises():
    """Completely invalid syntax raises a parse error."""
    with pytest.raises(Exception):
        RequirementsELTransformer.parse_el("not a valid expression !!!")
