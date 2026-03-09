# Copyright © LFV

import pytest

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.models import mvrs


@pytest.fixture
def mvr_data_1() -> mvrs.MVRData:
    return mvrs.MVRData(
        id=UrnId(urn="test", id="MVR_001"),
        svc_ids=[UrnId(urn="test", id="SVC_001"), UrnId(urn="test", id="SVC_002")],
        comment=None,
        passed=True,
    )


@pytest.fixture
def mvr_data_2() -> mvrs.MVRData:
    return mvrs.MVRData(
        id=UrnId(urn="test", id="MVR_002"),
        svc_ids=[UrnId(urn="test", id="SVC_201"), UrnId(urn="test", id="SVC_202")],
        comment="Some MVR comment",
        passed=False,
    )


@pytest.fixture
def mvrs_data(mvr_data_1: mvrs.MVRData, mvr_data_2: mvrs.MVRData) -> mvrs.MVRsData:
    return mvrs.MVRsData(
        results={
            UrnId(urn="test", id="MVR_001"): mvr_data_1,
            UrnId(urn="test", id="MVR_002"): mvr_data_2,
        }
    )


def test_mvr_data(mvr_data_2: mvrs.MVRData):
    assert mvr_data_2.id == UrnId(urn="test", id="MVR_002")
    assert mvr_data_2.svc_ids == [UrnId(urn="test", id="SVC_201"), UrnId(urn="test", id="SVC_202")]
    assert mvr_data_2.comment == "Some MVR comment"
    assert mvr_data_2.passed is False


def test_mvrs_data(mvrs_data: mvrs.MVRsData):
    assert len(mvrs_data.results) == 2
    assert UrnId(urn="test", id="MVR_001") in mvrs_data.results
    assert UrnId(urn="test", id="MVR_002") in mvrs_data.results
