# Copyright © LFV

from typing import Dict

import pytest

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.models import svcs


@pytest.fixture
def svc_filters() -> Dict[str, SVCFilter]:
    filters = {
        "sys-A": SVCFilter(
            urn_ids_imports={
                UrnId(urn="sys-A", id="SVC_001"),
                UrnId(urn="sys-A", id="SVC_002"),
            },
            urn_ids_excludes={
                UrnId(urn="sys-A", id="SVC_901"),
                UrnId(urn="sys-A", id="SVC_902"),
            },
        )
    }

    return filters


@pytest.fixture
def svc_data_1() -> svcs.SVCData:
    return svcs.SVCData(
        id=UrnId(urn="sys-A", id="SVC_001"),
        requirement_ids=[UrnId(urn="sys-A", id="REQ_001"), UrnId(urn="sys-A", id="REQ_002")],
        title="Title SVC_001",
        description="Description SVC_001",
        verification=svcs.VERIFICATIONTYPES.AUTOMATED_TEST,
        instructions="Some instructions SVC_001",
        revision="0.0.1",
    )


@pytest.fixture
def svc_data_2() -> svcs.SVCData:
    return svcs.SVCData(
        id=UrnId(urn="sys-A", id="SVC_002"),
        requirement_ids=[UrnId(urn="sys-A", id="REQ_201"), UrnId(urn="sys-A", id="REQ_202")],
        title="Title SVC_002",
        description="Description SVC_002",
        verification=svcs.VERIFICATIONTYPES.AUTOMATED_TEST,
        instructions="Some instructions SVC_002",
        revision="0.0.1",
    )


@pytest.fixture
def svcs_data(svc_data_1: svcs.SVCData, svc_data_2: svcs.SVCData, svc_filters) -> svcs.SVCsData:
    return svcs.SVCsData(
        cases={UrnId(urn="sys-A", id="SVC_001"): svc_data_1, UrnId(urn="sys-A", id="SVC_002"): svc_data_2},
        filters=svc_filters,
    )


def test_svcs_data(svcs_data: svcs.SVCsData):
    assert len(svcs_data.cases) == 2
    assert len(svcs_data.filters) == 1

    assert svcs_data.filters["sys-A"].urn_ids_imports == {
        UrnId(urn="sys-A", id="SVC_001"),
        UrnId(urn="sys-A", id="SVC_002"),
    }
    assert svcs_data.filters["sys-A"].urn_ids_excludes == {
        UrnId(urn="sys-A", id="SVC_901"),
        UrnId(urn="sys-A", id="SVC_902"),
    }


def test_svc_data(svc_data_1: svcs.SVCData, svc_data_2: svcs.SVCData):
    assert svc_data_1.id == UrnId(urn="sys-A", id="SVC_001")
    assert svc_data_1.requirement_ids == [UrnId(urn="sys-A", id="REQ_001"), UrnId(urn="sys-A", id="REQ_002")]
    assert svc_data_1.title == "Title SVC_001"
    assert svc_data_1.description == "Description SVC_001"
    assert svc_data_1.verification == svcs.VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc_data_1.instructions == "Some instructions SVC_001"
    assert str(svc_data_1.revision) == "0.0.1"

    assert svc_data_2.id == UrnId(urn="sys-A", id="SVC_002")
    assert svc_data_2.requirement_ids == [UrnId(urn="sys-A", id="REQ_201"), UrnId(urn="sys-A", id="REQ_202")]
    assert svc_data_2.title == "Title SVC_002"
    assert svc_data_2.description == "Description SVC_002"
    assert svc_data_2.verification == svcs.VERIFICATIONTYPES.AUTOMATED_TEST
    assert svc_data_2.instructions == "Some instructions SVC_002"
    assert str(svc_data_2.revision) == "0.0.1"
