# Copyright © LFV

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
