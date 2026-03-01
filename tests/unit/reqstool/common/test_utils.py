# Copyright © LFV


from reqstool.common.utils import Utils


def test_check_ids_to_filter_plain_ids_get_urn_prepended():
    result = Utils.check_ids_to_filter(ids=["REQ_001", "REQ_002"], current_urn="ms-001")
    assert result == ["ms-001:REQ_001", "ms-001:REQ_002"]


def test_check_ids_to_filter_qualified_id_with_matching_urn_is_kept():
    result = Utils.check_ids_to_filter(ids=["ms-001:REQ_001"], current_urn="ms-001")
    assert result == ["ms-001:REQ_001"]


def test_check_ids_to_filter_qualified_id_with_foreign_urn_is_excluded():
    result = Utils.check_ids_to_filter(ids=["other-urn:REQ_001"], current_urn="ms-001")
    assert result == []


def test_check_ids_to_filter_mixed_ids():
    result = Utils.check_ids_to_filter(ids=["REQ_001", "ms-001:REQ_002", "other-urn:REQ_003"], current_urn="ms-001")
    assert "ms-001:REQ_001" in result
    assert "ms-001:REQ_002" in result
    assert "other-urn:REQ_003" not in result


def test_create_accessible_nodes_dict():
    parsing_graph: dict = {
        "ext-001": [],
        "ext-002": [],
        "sys-001": ["ext-001", "ext-002", "ms-001"],
        "ms-001": ["sys-001"],
    }

    accesible_nodes_dict = Utils.create_accessible_nodes_dict(parsing_graph)

    assert accesible_nodes_dict
