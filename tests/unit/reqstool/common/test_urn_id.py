# Copyright © LFV

import pytest

from reqstool.common.dataclasses.urn_id import UrnId


def test_assure_urn_id_bare_id_returns_urn_id():
    result = UrnId.assure_urn_id(urn="ms-001", id="REQ_001")
    assert isinstance(result, UrnId)
    assert result.urn == "ms-001"
    assert result.id == "REQ_001"
    assert str(result) == "ms-001:REQ_001"


def test_assure_urn_id_qualified_id_uses_embedded_urn():
    result = UrnId.assure_urn_id(urn="ms-001", id="other-urn:REQ_999")
    assert isinstance(result, UrnId)
    assert result.urn == "other-urn"
    assert result.id == "REQ_999"
    assert str(result) == "other-urn:REQ_999"


def test_assure_urn_id_qualified_same_urn():
    result = UrnId.assure_urn_id(urn="ms-001", id="ms-001:REQ_042")
    assert isinstance(result, UrnId)
    assert result.urn == "ms-001"
    assert result.id == "REQ_042"


# ---------------------------------------------------------------------------
# UrnId.instance — negative paths
# ---------------------------------------------------------------------------


def test_urn_id_instance_valid():
    uid = UrnId.instance("ms-001:REQ_001")
    assert uid.urn == "ms-001"
    assert uid.id == "REQ_001"


def test_urn_id_instance_no_separator_raises():
    """UrnId.instance requires a ':' separator; bare id raises ValueError."""
    with pytest.raises(ValueError):
        UrnId.instance("no-separator-here")


def test_urn_id_instance_multiple_separators_splits_on_first():
    """UrnId.instance splits on the FIRST ':' only."""
    uid = UrnId.instance("ms-001:REQ:extra")
    assert uid.urn == "ms-001"
    assert uid.id == "REQ:extra"


# ---------------------------------------------------------------------------
# __str__ and ordering
# ---------------------------------------------------------------------------


def test_urn_id_str_representation():
    assert str(UrnId(urn="ms-001", id="REQ_001")) == "ms-001:REQ_001"


def test_urn_id_ordering_by_id():
    a = UrnId(urn="ms-001", id="REQ_001")
    b = UrnId(urn="ms-001", id="REQ_002")
    assert a < b
    assert not b < a


def test_urn_id_ordering_by_urn():
    a = UrnId(urn="ms-001", id="REQ_001")
    c = UrnId(urn="ns-002", id="REQ_001")
    assert a < c


def test_urn_id_equality():
    assert UrnId(urn="ms-001", id="REQ_001") == UrnId(urn="ms-001", id="REQ_001")
    assert UrnId(urn="ms-001", id="REQ_001") != UrnId(urn="ms-001", id="REQ_002")
