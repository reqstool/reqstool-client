# Copyright © LFV

from unittest.mock import MagicMock

from reqstool.commands.status.statistics_generator import StatisticsGenerator
from reqstool.common.dataclasses.urn_id import UrnId


def _make_generator():
    """Create a StatisticsGenerator bypassing __init__."""
    gen = object.__new__(StatisticsGenerator)
    gen.cid = MagicMock()
    return gen


# ---------------------------------------------------------------------------
# _get_urn_ids_for_svcs
# ---------------------------------------------------------------------------

REQ_1 = UrnId(urn="urn", id="REQ_001")
REQ_2 = UrnId(urn="urn", id="REQ_002")
SVC_1 = UrnId(urn="urn", id="SVC_001")
SVC_2 = UrnId(urn="urn", id="SVC_002")
SVC_3 = UrnId(urn="urn", id="SVC_003")
MVR_1 = UrnId(urn="urn", id="MVR_001")
MVR_2 = UrnId(urn="urn", id="MVR_002")


def test_get_urn_ids_for_svcs_returns_matching():
    gen = _make_generator()
    svcs_from_req = {REQ_1: [SVC_1, SVC_2], REQ_2: [SVC_3]}
    result = gen._get_urn_ids_for_svcs(urn_id=REQ_1, svcs_from_req=svcs_from_req)
    assert result == [SVC_1, SVC_2]


def test_get_urn_ids_for_svcs_returns_empty_for_missing_key():
    gen = _make_generator()
    svcs_from_req = {REQ_2: [SVC_3]}
    result = gen._get_urn_ids_for_svcs(urn_id=REQ_1, svcs_from_req=svcs_from_req)
    assert result == []


def test_get_urn_ids_for_svcs_empty_dict():
    gen = _make_generator()
    result = gen._get_urn_ids_for_svcs(urn_id=REQ_1, svcs_from_req={})
    assert result == []


# ---------------------------------------------------------------------------
# _get_nr_of_impls_for_req
# ---------------------------------------------------------------------------


def test_get_nr_of_impls_for_req_single():
    gen = _make_generator()
    gen.cid.annotations_impls = {REQ_1: ["annotation_1"]}
    assert gen._get_nr_of_impls_for_req(urn_id=REQ_1) == 1


def test_get_nr_of_impls_for_req_multiple():
    gen = _make_generator()
    gen.cid.annotations_impls = {REQ_1: ["annotation_1", "annotation_2"]}
    assert gen._get_nr_of_impls_for_req(urn_id=REQ_1) == 2


def test_get_nr_of_impls_for_req_missing():
    gen = _make_generator()
    gen.cid.annotations_impls = {REQ_2: ["some_annotation"]}
    assert gen._get_nr_of_impls_for_req(urn_id=REQ_1) == 0


def test_get_nr_of_impls_for_req_empty():
    gen = _make_generator()
    gen.cid.annotations_impls = {}
    assert gen._get_nr_of_impls_for_req(urn_id=REQ_1) == 0


# ---------------------------------------------------------------------------
# _get_mvr_ids_for_req
# ---------------------------------------------------------------------------


def test_get_mvr_ids_for_req_returns_matching():
    gen = _make_generator()
    gen.cid.mvrs_from_svc = {SVC_1: [MVR_1], SVC_2: [MVR_2]}
    result = gen._get_mvr_ids_for_req(svcs_urn_ids=[SVC_1, SVC_2])
    assert result == [MVR_1, MVR_2]


def test_get_mvr_ids_for_req_missing_svc():
    gen = _make_generator()
    gen.cid.mvrs_from_svc = {SVC_2: [MVR_2]}
    result = gen._get_mvr_ids_for_req(svcs_urn_ids=[SVC_1])
    assert result == []


def test_get_mvr_ids_for_req_empty():
    gen = _make_generator()
    gen.cid.mvrs_from_svc = {}
    result = gen._get_mvr_ids_for_req(svcs_urn_ids=[])
    assert result == []
